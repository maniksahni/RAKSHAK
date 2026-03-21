import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import query_db, log_audit
from socket_events import emit_risk_update, emit_sos_alert
from healer import validate_coords
from datetime import datetime, timedelta

log = logging.getLogger('rakshak')

ai_bp = Blueprint('ai', __name__)


def get_socketio():
    from app import socketio
    return socketio


RISK_THRESHOLDS = {
    'low':    {'min': 0, 'max': 1},
    'medium': {'min': 2, 'max': 2},
    'high':   {'min': 3, 'max': 999},
}
AUTO_SOS_THRESHOLD = 3   # consecutive missed pings before auto-SOS
PING_INTERVAL_SEC  = 120  # JS pings every 2 minutes


# ── Heartbeat Ping ────────────────────────────────────────────────────────────
@ai_bp.route('/ping', methods=['POST'])
@login_required
def ping():
    """JS calls this every 2 minutes. Updates last_ping and resets counters."""
    try:
        data    = request.get_json() or {}
        raw_lat = data.get('lat')
        raw_lng = data.get('lng')

        # Validate coordinates if provided
        lat, lng = None, None
        if raw_lat is not None and raw_lng is not None:
            try:
                lat, lng = validate_coords(raw_lat, raw_lng)
            except ValueError:
                lat, lng = None, None   # store null if invalid, don't block ping

        now = datetime.now()
        query_db(
            """UPDATE users
               SET last_ping=%s, consecutive_missed_pings=0
               WHERE id=%s""",
            (now, current_user.id), commit=True
        )
        query_db(
            """INSERT INTO ping_logs (user_id, ping_type, latitude, longitude)
               VALUES (%s, 'heartbeat', %s, %s)""",
            (current_user.id, lat, lng), commit=True
        )

        # Recalculate risk
        risk_level = 'low'
        query_db(
            'UPDATE users SET risk_level=%s WHERE id=%s',
            (risk_level, current_user.id), commit=True
        )

        return jsonify(success=True, risk_level=risk_level, timestamp=now.isoformat())

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Check Missed Pings (called server-side or via JS fallback) ────────────────
@ai_bp.route('/check-missed', methods=['POST'])
@login_required
def check_missed():
    """
    Called by a background task / admin. Checks for users who have not
    pinged in > 2 minutes and escalates their risk level.
    """
    try:
        cutoff = datetime.now() - timedelta(seconds=PING_INTERVAL_SEC + 30)
        # Users who were last pinged before cutoff
        stale_users = query_db(
            """SELECT id, consecutive_missed_pings, full_name, email
               FROM users
               WHERE is_active=TRUE AND role='user'
                 AND last_ping IS NOT NULL
                 AND last_ping < %s""",
            (cutoff,)
        )

        for u in stale_users:
            missed = u['consecutive_missed_pings'] + 1
            query_db(
                'UPDATE users SET consecutive_missed_pings=%s WHERE id=%s',
                (missed, u['id']), commit=True
            )
            query_db(
                "INSERT INTO ping_logs (user_id, ping_type) VALUES (%s, 'missed')",
                (u['id'],), commit=True
            )

            # Calculate risk
            if missed >= AUTO_SOS_THRESHOLD:
                risk = 'high'
            elif missed >= 2:
                risk = 'medium'
            else:
                risk = 'low'

            query_db('UPDATE users SET risk_level=%s WHERE id=%s', (risk, u['id']), commit=True)
            emit_risk_update(get_socketio(), u['id'], risk)

            # Auto-SOS if threshold reached
            if missed == AUTO_SOS_THRESHOLD:
                _trigger_auto_sos(u['id'])

        return jsonify(success=True, checked=len(stale_users))

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


def _trigger_auto_sos(user_id):
    """Automatically trigger an SOS alert for inactive user."""
    try:
        # Get last known location
        last_ping = query_db(
            """SELECT latitude, longitude FROM ping_logs
               WHERE user_id=%s AND latitude IS NOT NULL
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,), one=True
        )
        lat = last_ping['latitude'] if last_ping else 0
        lng = last_ping['longitude'] if last_ping else 0

        alert_id = query_db(
            """INSERT INTO sos_alerts
               (user_id, latitude, longitude, trigger_type, message)
               VALUES (%s, %s, %s, 'auto_ai', 'Auto-triggered: No heartbeat detected for 6+ minutes') RETURNING id""",
            (user_id, lat, lng), commit=True
        )
        # Log
        query_db(
            "INSERT INTO ping_logs (user_id, ping_type) VALUES (%s, 'auto_sos')",
            (user_id,), commit=True
        )
        log_audit(user_id, 'auto_sos_triggered', 'sos_alerts', alert_id)

        # Notify contacts
        contacts = query_db(
            'SELECT * FROM trusted_contacts WHERE user_id=%s', (user_id,)
        )
        contact_user_ids = []
        for c in contacts:
            cu = query_db('SELECT id FROM users WHERE email=%s', (c['contact_email'],), one=True)
            if cu:
                contact_user_ids.append(cu['id'])

        user_info = query_db('SELECT full_name FROM users WHERE id=%s', (user_id,), one=True)
        name = user_info['full_name'] if user_info else 'User'
        emit_sos_alert(get_socketio(), {
            'id': alert_id, 'user_id': user_id,
            'latitude': lat, 'longitude': lng,
            'trigger_type': 'auto_ai',
            'message': f'AUTO SOS: {name} stopped responding'
        }, contact_user_ids, user_id)

    except Exception as e:
        log.error(f'Auto-SOS failed for user {user_id}: {e}')


# ── Risk Score API ────────────────────────────────────────────────────────────
@ai_bp.route('/risk-score')
@login_required
def get_risk_score():
    """Returns current user's risk level."""
    try:
        data = query_db(
            'SELECT risk_level, consecutive_missed_pings, last_ping FROM users WHERE id=%s',
            (current_user.id,), one=True
        )
        result = dict(data) if data else {}
        if result.get('last_ping') and hasattr(result['last_ping'], 'isoformat'):
            result['last_ping'] = result['last_ping'].isoformat()
        return jsonify(success=True, **result)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Admin: All User Risk Scores ───────────────────────────────────────────────
@ai_bp.route('/risk-all')
@login_required
def get_all_risk_scores():
    """Admin only: live risk scores for all users."""
    if not current_user.is_admin:
        return jsonify(success=False, error='Forbidden'), 403
    try:
        rows = query_db(
            """SELECT id, full_name, email, phone, risk_level,
                      consecutive_missed_pings, last_ping
               FROM users WHERE role='user' AND is_active=TRUE
               ORDER BY
                 CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                 last_ping DESC"""
        )
        result = []
        for r in rows:
            d = dict(r)
            if d.get('last_ping') and hasattr(d['last_ping'], 'isoformat'):
                d['last_ping'] = d['last_ping'].isoformat()
            result.append(d)
        return jsonify(success=True, users=result)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
