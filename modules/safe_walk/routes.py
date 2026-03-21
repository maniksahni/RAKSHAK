import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from flask import (Blueprint, render_template, request, jsonify, abort)
from flask_login import login_required, current_user
from models import query_db, log_audit

log = logging.getLogger('rakshak')

safe_walk_bp = Blueprint('safe_walk', __name__)


def _safe_journey(row):
    """Serialise a journey row for JSON responses."""
    if not row:
        return None
    d = {}
    for k, v in dict(row).items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
        elif isinstance(v, Decimal):
            d[k] = float(v)
        else:
            d[k] = v
    return d


# ── Dashboard page ────────────────────────────────────────────────────────────
@safe_walk_bp.route('/')
@login_required
def index():
    return render_template('dashboard/safe_walk.html')


# ── Start Journey ─────────────────────────────────────────────────────────────
@safe_walk_bp.route('/start', methods=['POST'])
@login_required
def start_journey():
    try:
        data = request.get_json() or {}
        start_lat = data.get('start_lat')
        start_lng = data.get('start_lng')
        dest_lat = data.get('dest_lat')
        dest_lng = data.get('dest_lng')
        eta_minutes = data.get('eta_minutes', 30)

        if None in (start_lat, start_lng, dest_lat, dest_lng):
            return jsonify(success=False, error='Start and destination coordinates are required.'), 400

        try:
            start_lat = float(start_lat)
            start_lng = float(start_lng)
            dest_lat = float(dest_lat)
            dest_lng = float(dest_lng)
            eta_minutes = int(eta_minutes)
        except (TypeError, ValueError):
            return jsonify(success=False, error='Invalid coordinate or ETA values.'), 400

        # Only one active journey at a time
        existing = query_db(
            "SELECT id FROM journeys WHERE user_id=%s AND status='active'",
            (current_user.id,), one=True
        )
        if existing:
            return jsonify(success=False, error='You already have an active journey. End it first.'), 409

        share_token = secrets.token_urlsafe(32)
        expected_end = datetime.now() + timedelta(minutes=eta_minutes)

        journey_id = query_db(
            """INSERT INTO journeys
               (user_id, start_lat, start_lng, dest_lat, dest_lng,
                current_lat, current_lng, eta_minutes, expected_end, share_token, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')""",
            (current_user.id, start_lat, start_lng, dest_lat, dest_lng,
             start_lat, start_lng, eta_minutes, expected_end, share_token),
            commit=True
        )

        log_audit(current_user.id, 'journey_started', 'journeys', journey_id,
                  ip_address=request.remote_addr)

        journey = query_db('SELECT * FROM journeys WHERE id=%s', (journey_id,), one=True)

        return jsonify(
            success=True,
            journey=_safe_journey(journey),
            share_token=share_token,
            message='Journey started! Stay safe.'
        )

    except Exception as e:
        log.error(f'Start journey failed for user {current_user.id}: {e}')
        return jsonify(success=False, error='Failed to start journey.'), 500


# ── Update Location ───────────────────────────────────────────────────────────
@safe_walk_bp.route('/update', methods=['POST'])
@login_required
def update_location():
    try:
        data = request.get_json() or {}
        lat = data.get('latitude')
        lng = data.get('longitude')

        if lat is None or lng is None:
            return jsonify(success=False, error='Location is required.'), 400

        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return jsonify(success=False, error='Invalid coordinates.'), 400

        journey = query_db(
            "SELECT id FROM journeys WHERE user_id=%s AND status='active'",
            (current_user.id,), one=True
        )
        if not journey:
            return jsonify(success=False, error='No active journey found.'), 404

        query_db(
            'UPDATE journeys SET current_lat=%s, current_lng=%s WHERE id=%s',
            (lat, lng, journey['id']), commit=True
        )

        return jsonify(success=True, message='Location updated.')

    except Exception as e:
        log.error(f'Update journey location failed: {e}')
        return jsonify(success=False, error='Failed to update location.'), 500


# ── End Journey ───────────────────────────────────────────────────────────────
@safe_walk_bp.route('/end', methods=['POST'])
@login_required
def end_journey():
    try:
        journey = query_db(
            "SELECT id FROM journeys WHERE user_id=%s AND status='active'",
            (current_user.id,), one=True
        )
        if not journey:
            return jsonify(success=False, error='No active journey found.'), 404

        query_db(
            """UPDATE journeys SET status='completed', ended_at=%s WHERE id=%s""",
            (datetime.now(), journey['id']), commit=True
        )

        log_audit(current_user.id, 'journey_ended', 'journeys', journey['id'],
                  ip_address=request.remote_addr)

        return jsonify(success=True, message='Journey ended. Glad you are safe!')

    except Exception as e:
        log.error(f'End journey failed: {e}')
        return jsonify(success=False, error='Failed to end journey.'), 500


# ── Check ETA ─────────────────────────────────────────────────────────────────
@safe_walk_bp.route('/check-eta', methods=['POST'])
@login_required
def check_eta():
    try:
        journey = query_db(
            "SELECT * FROM journeys WHERE user_id=%s AND status='active'",
            (current_user.id,), one=True
        )
        if not journey:
            return jsonify(success=False, error='No active journey found.'), 404

        expected = journey['expected_end']
        now = datetime.now()
        is_overdue = now > expected if expected else False

        if is_overdue and journey['status'] == 'active':
            query_db(
                "UPDATE journeys SET status='overdue' WHERE id=%s",
                (journey['id'],), commit=True
            )

            # Notify trusted contacts
            contacts = query_db(
                'SELECT contact_name, contact_email FROM trusted_contacts WHERE user_id=%s',
                (current_user.id,)
            )
            for c in contacts:
                cu = query_db('SELECT id FROM users WHERE email=%s',
                              (c['contact_email'],), one=True)
                if cu:
                    query_db(
                        """INSERT INTO notifications (user_id, title, message, notification_type)
                           VALUES (%s, %s, %s, 'alert')""",
                        (cu['id'],
                         f'Journey overdue: {current_user.full_name}',
                         f'{current_user.full_name} has not reached their destination. Journey is overdue.'),
                        commit=True
                    )

            log_audit(current_user.id, 'journey_overdue', 'journeys', journey['id'],
                      ip_address=request.remote_addr)

            return jsonify(success=True, overdue=True,
                           message='Journey is overdue! Trusted contacts have been notified.')

        remaining = (expected - now).total_seconds() if expected else 0
        return jsonify(success=True, overdue=False,
                       remaining_seconds=max(0, int(remaining)))

    except Exception as e:
        log.error(f'Check ETA failed: {e}')
        return jsonify(success=False, error='Failed to check ETA.'), 500


# ── Active Journey Status ─────────────────────────────────────────────────────
@safe_walk_bp.route('/active')
@login_required
def active_journey():
    try:
        journey = query_db(
            "SELECT * FROM journeys WHERE user_id=%s AND status IN ('active','overdue') ORDER BY created_at DESC LIMIT 1",
            (current_user.id,), one=True
        )
        if not journey:
            return jsonify(success=True, journey=None)

        return jsonify(success=True, journey=_safe_journey(journey))

    except Exception as e:
        log.error(f'Get active journey failed: {e}')
        return jsonify(success=False, error='Failed to fetch journey.'), 500


# ── Public Share Tracking ─────────────────────────────────────────────────────
@safe_walk_bp.route('/share/<token>')
def track_journey(token):
    """Public page — no login required. Trusted contacts can track the journey."""
    journey = query_db(
        'SELECT * FROM journeys WHERE share_token=%s', (token,), one=True
    )
    if not journey:
        abort(404)

    user = query_db('SELECT full_name FROM users WHERE id=%s',
                    (journey['user_id'],), one=True)
    name = user['full_name'] if user else 'Someone'

    return render_template('safe_walk/track.html',
                           journey=_safe_journey(journey),
                           person_name=name,
                           token=token)


# ── API: Get journey data for public tracking (AJAX polling) ──────────────────
@safe_walk_bp.route('/share/<token>/data')
def track_journey_data(token):
    """JSON endpoint for live-polling the journey location."""
    journey = query_db(
        'SELECT * FROM journeys WHERE share_token=%s', (token,), one=True
    )
    if not journey:
        return jsonify(success=False, error='Journey not found.'), 404

    return jsonify(success=True, journey=_safe_journey(journey))
