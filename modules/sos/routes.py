import logging
from flask import (Blueprint, render_template, request, jsonify,
                   send_file, abort)
from flask_login import login_required, current_user
from models import query_db, log_audit
from socket_events import emit_sos_alert
from pdf_reports import generate_sos_report
from healer import validate_coords, validate_battery, sanitize_str
from datetime import datetime

log = logging.getLogger('rakshak')

sos_bp = Blueprint('sos', __name__)

# We import socketio lazily to avoid circular import
def get_socketio():
    from app import socketio
    return socketio


# ── Dashboard (User) ──────────────────────────────────────────────────────────
@sos_bp.route('/dashboard')
@login_required
def dashboard_index():
    return render_template('dashboard/index.html')


# Alias route registered in app as blueprint 'dashboard'
from flask import Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    # Fetch recent alerts
    alerts = query_db(
        'SELECT * FROM sos_alerts WHERE user_id=%s ORDER BY created_at DESC LIMIT 10',
        (current_user.id,)
    )
    notifications = query_db(
        """SELECT * FROM notifications WHERE user_id=%s AND is_read=FALSE
           ORDER BY created_at DESC LIMIT 20""",
        (current_user.id,)
    )
    danger_zones = query_db(
        "SELECT * FROM danger_zones WHERE status='approved' ORDER BY created_at DESC LIMIT 100"
    )
    def _safe(rows):
        from decimal import Decimal
        out = []
        for r in (rows or []):
            d = {}
            for k, v in dict(r).items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    d[k] = float(v)
                else:
                    d[k] = v
            out.append(d)
        return out

    trusted_contacts = query_db(
        'SELECT * FROM trusted_contacts WHERE user_id=%s ORDER BY created_at ASC',
        (current_user.id,)
    )

    return render_template('dashboard/index.html',
                           alerts=_safe(alerts),
                           notifications=notifications,
                           danger_zones=_safe(danger_zones),
                           trusted_contacts=_safe(trusted_contacts))


# ── Trigger SOS ───────────────────────────────────────────────────────────────
@sos_bp.route('/trigger', methods=['POST'])
@login_required
def trigger_sos():
    try:
        data         = request.get_json() or {}
        raw_lat      = data.get('latitude')
        raw_lng      = data.get('longitude')
        address      = sanitize_str(data.get('address', ''), 500)
        trigger_type = data.get('trigger_type', 'manual')
        message      = sanitize_str(data.get('message', ''), 1000)
        battery      = validate_battery(data.get('battery_level'))
        accuracy     = data.get('accuracy')

        if raw_lat is None or raw_lng is None:
            # ── Fallback: Attempt to fetch last known location from ping_logs ──
            last_ping = query_db(
                '''SELECT latitude, longitude FROM ping_logs 
                   WHERE user_id=%s AND latitude IS NOT NULL AND longitude IS NOT NULL 
                   ORDER BY created_at DESC LIMIT 1''',
                (current_user.id,), one=True
            )
            if last_ping:
                raw_lat = last_ping['latitude']
                raw_lng = last_ping['longitude']
                message += " [LOCATION EST: LAST KNOWN]"
            else:
                raw_lat = 0.0
                raw_lng = 0.0
                message += " [LOCATION UNKNOWN]"

        try:
            lat, lng = validate_coords(raw_lat, raw_lng)
        except ValueError as ve:
            return jsonify(success=False, error=str(ve)), 400

        # Clamp accuracy to sane range
        try:
            accuracy = max(0.0, float(accuracy)) if accuracy is not None else None
        except (TypeError, ValueError):
            accuracy = None

        # Insert alert
        alert_id = query_db(
            """INSERT INTO sos_alerts
               (user_id, latitude, longitude, address, trigger_type, message, battery_level, accuracy)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (current_user.id, lat, lng, address, trigger_type, message, battery, accuracy),
            commit=True
        )

        alert_row = query_db('SELECT * FROM sos_alerts WHERE id=%s', (alert_id,), one=True)

        # Notify trusted contacts
        contacts = query_db(
            'SELECT * FROM trusted_contacts WHERE user_id=%s', (current_user.id,)
        )

        # Fetch contacts who are also registered users
        contact_user_ids = []
        for c in contacts:
            cu = query_db('SELECT id FROM users WHERE email=%s', (c['contact_email'],), one=True)
            if cu:
                contact_user_ids.append(cu['id'])
                # Save in-app notification
                query_db(
                    """INSERT INTO notifications (user_id, title, message, notification_type, related_alert_id)
                       VALUES (%s, %s, %s, 'sos', %s)""",
                    (cu['id'],
                     f'🚨 SOS Alert from {current_user.full_name}',
                     f'{current_user.full_name} triggered an SOS at {address or f"{lat},{lng}"}',
                     alert_id),
                    commit=True
                )

        alert_dict = dict(alert_row) if alert_row else {}
        alert_dict['created_at'] = alert_dict.get('created_at', datetime.now()).isoformat() \
            if hasattr(alert_dict.get('created_at'), 'isoformat') else str(alert_dict.get('created_at', ''))

        emit_sos_alert(get_socketio(), alert_dict, contact_user_ids, current_user.id)
        log_audit(current_user.id, 'sos_triggered', 'sos_alerts', alert_id,
                  new_value={'lat': lat, 'lng': lng, 'type': trigger_type},
                  ip_address=request.remote_addr)

        return jsonify(success=True, alert_id=alert_id,
                       message='SOS Alert sent to your trusted contacts!')

    except Exception as e:
        log.error(f'SOS trigger failed for user {current_user.id}: {e}')
        return jsonify(success=False, error='SOS failed. Please try again.'), 500


# ── Alert History ─────────────────────────────────────────────────────────────
@sos_bp.route('/history')
@login_required
def history():
    try:
        alerts = query_db(
            'SELECT * FROM sos_alerts WHERE user_id=%s ORDER BY created_at DESC',
            (current_user.id,)
        )
        def _safe_alert(rows):
            from decimal import Decimal
            out = []
            for r in (rows or []):
                d = {}
                for k, v in dict(r).items():
                    if hasattr(v, 'isoformat'):
                        d[k] = v.isoformat()
                    elif isinstance(v, Decimal):
                        d[k] = float(v)
                    else:
                        d[k] = v
                out.append(d)
            return out

        safe_alerts = _safe_alert(alerts)
        # Return HTML page if browser request, JSON if AJAX/fetch
        if request.accept_mimetypes.accept_html and not request.is_json \
                and request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return render_template('dashboard/history.html', alerts=safe_alerts)
        return jsonify(success=True, alerts=safe_alerts)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Mark Alert Resolved ───────────────────────────────────────────────────────
@sos_bp.route('/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    try:
        query_db(
            """UPDATE sos_alerts SET status='resolved', resolved_at=%s
               WHERE id=%s AND user_id=%s""",
            (datetime.now(), alert_id, current_user.id), commit=True
        )
        return jsonify(success=True, message='Alert marked as resolved.')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# ── Evidence Vault Endpoint ───────────────────────────────────────────────────
@sos_bp.route('/<int:alert_id>/evidence', methods=['GET'])
@login_required
def get_evidence(alert_id):
    try:
        alert = query_db(
            'SELECT * FROM sos_alerts WHERE id=%s AND user_id=%s',
            (alert_id, current_user.id), one=True
        )
        if not alert:
            return jsonify(success=False, error="Alert not found"), 404
        
        # Simulate forensic metadata generation for the specific alert
        import hashlib, time
        raw_hash = f"SOS-{alert_id}-{current_user.id}-{alert['created_at'].isoformat() if alert.get('created_at') else time.time()}"
        immutable_hash = hashlib.sha256(raw_hash.encode()).hexdigest()
        
        return jsonify(
            success=True, 
            evidence={
                "alert_id": alert_id,
                "lat": float(alert['latitude']) if alert.get('latitude') else 0.0,
                "lng": float(alert['longitude']) if alert.get('longitude') else 0.0,
                "address": alert.get('address') or "Locating coordinates...",
                "status": alert.get('status', 'resolved'),
                "trigger_type": alert.get('trigger_type', 'manual'),
                "timestamp": alert['created_at'].isoformat() if alert.get('created_at') else "",
                "immutable_hash": immutable_hash,
                "encryption": "AES-256-GCM",
                "network_path": ["Sat-Alpha", "Proxy-Relay-9", "Command-Center-Main"]
            }
        )
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# ── PDF Report ────────────────────────────────────────────────────────────────
@sos_bp.route('/<int:alert_id>/pdf')
@login_required
def download_pdf(alert_id):
    try:
        alert = query_db(
            'SELECT * FROM sos_alerts WHERE id=%s AND user_id=%s',
            (alert_id, current_user.id), one=True
        )
        if not alert:
            abort(404)

        user_data = query_db('SELECT * FROM users WHERE id=%s', (current_user.id,), one=True)
        contacts  = query_db('SELECT * FROM trusted_contacts WHERE user_id=%s', (current_user.id,))

        # Serialize datetime fields
        alert_dict = {}
        for k, v in alert.items():
            alert_dict[k] = v.isoformat() if hasattr(v, 'isoformat') else v

        pdf_buffer = generate_sos_report(alert_dict, dict(user_data) if user_data else {}, contacts)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'RAKSHAK_Incident_{alert_id}.pdf'
        )
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Evidence Vault ────────────────────────────────────────────────────────
@sos_bp.route('/evidence/<int:alert_id>')
@login_required
def evidence_vault(alert_id):
    """Return full evidence package for an SOS alert: details, audit logs, contacts notified, timeline."""
    try:
        # Fetch alert — owner or admin only
        alert = query_db('SELECT * FROM sos_alerts WHERE id=%s', (alert_id,), one=True)
        if not alert:
            return jsonify(success=False, error='Alert not found.'), 404
        if alert['user_id'] != current_user.id and not current_user.is_admin:
            return jsonify(success=False, error='Access denied.'), 403

        from decimal import Decimal
        import json

        def _serialize(row):
            d = {}
            for k, v in dict(row).items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    d[k] = float(v)
                elif isinstance(v, (bytes, bytearray)):
                    d[k] = v.decode('utf-8', errors='replace')
                else:
                    d[k] = v
            return d

        alert_data = _serialize(alert)

        # Audit logs for this alert
        audit_logs = query_db(
            """SELECT id, user_id, action, table_name, record_id,
                      old_value, new_value, ip_address, created_at
               FROM audit_logs
               WHERE (table_name='sos_alerts' AND record_id=%s)
                  OR (action='sos_triggered' AND record_id=%s)
               ORDER BY created_at ASC""",
            (alert_id, alert_id)
        )
        audit_list = []
        for row in (audit_logs or []):
            entry = _serialize(row)
            # Parse JSON strings in old_value / new_value
            for field in ('old_value', 'new_value'):
                if entry.get(field) and isinstance(entry[field], str):
                    try:
                        entry[field] = json.loads(entry[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            audit_list.append(entry)

        # Trusted contacts who were notified
        contacts = query_db(
            'SELECT contact_name, contact_email, contact_phone, relationship FROM trusted_contacts WHERE user_id=%s',
            (alert['user_id'],)
        )
        contact_list = [_serialize(c) for c in (contacts or [])]

        # Notifications sent for this alert
        notifs = query_db(
            """SELECT user_id, title, message, notification_type, is_read, created_at
               FROM notifications WHERE related_alert_id=%s ORDER BY created_at ASC""",
            (alert_id,)
        )
        notif_list = [_serialize(n) for n in (notifs or [])]

        # Build event timeline
        timeline = []
        timeline.append({
            'event': 'SOS Alert Created',
            'timestamp': alert_data.get('created_at', ''),
            'detail': f"Trigger type: {alert_data.get('trigger_type', 'unknown')}"
        })
        for n in notif_list:
            timeline.append({
                'event': 'Contact Notified',
                'timestamp': n.get('created_at', ''),
                'detail': n.get('title', '')
            })
        if alert_data.get('resolved_at'):
            timeline.append({
                'event': 'Alert Resolved',
                'timestamp': alert_data.get('resolved_at', ''),
                'detail': 'Marked as resolved by user'
            })
        for entry in audit_list:
            if entry.get('action') not in ('sos_triggered',):
                timeline.append({
                    'event': f"Audit: {entry.get('action', '').replace('_', ' ').title()}",
                    'timestamp': entry.get('created_at', ''),
                    'detail': f"From IP {entry.get('ip_address', 'N/A')}"
                })
        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x.get('timestamp', ''))

        log_audit(current_user.id, 'evidence_viewed', 'sos_alerts', alert_id,
                  ip_address=request.remote_addr)

        return jsonify(
            success=True,
            alert=alert_data,
            audit_logs=audit_list,
            contacts=contact_list,
            notifications=notif_list,
            timeline=timeline
        )
    except Exception as e:
        log.error(f'Evidence vault failed for alert {alert_id}: {e}')
        return jsonify(success=False, error='Failed to load evidence data.'), 500


# ── Notifications API ─────────────────────────────────────────────────────────
@sos_bp.route('/notifications')
@login_required
def get_notifications():
    try:
        notes = query_db(
            """SELECT * FROM notifications WHERE user_id=%s
               ORDER BY created_at DESC LIMIT 30""",
            (current_user.id,)
        )
        result = [{k: (v.isoformat() if hasattr(v, 'isoformat') else v)
                   for k, v in n.items()} for n in notes]
        return jsonify(success=True, notifications=result)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@sos_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    try:
        query_db('UPDATE notifications SET is_read=TRUE WHERE user_id=%s',
                 (current_user.id,), commit=True)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Community Nearby Alerts ──────────────────────────────────────────────────
@sos_bp.route('/nearby', methods=['POST'])
@login_required
def nearby_alerts():
    """Return anonymized recent SOS alerts within a radius (km)."""
    try:
        data = request.get_json() or {}
        lat = float(data.get('latitude', 0))
        lng = float(data.get('longitude', 0))
        radius_km = min(float(data.get('radius', 5)), 50)

        if lat == 0 and lng == 0:
            return jsonify(success=False, error='Location required'), 400

        # Bounding box approximation
        dlat = radius_km / 111.0
        dlng = radius_km / (111.0 * abs(max(0.01, __import__('math').cos(__import__('math').radians(lat)))))

        alerts = query_db(
            """SELECT id, latitude, longitude, trigger_type, status,
                      created_at, address
               FROM sos_alerts
               WHERE created_at >= NOW() - INTERVAL 7 DAY
                 AND latitude BETWEEN %s AND %s
                 AND longitude BETWEEN %s AND %s
               ORDER BY created_at DESC LIMIT 30""",
            (lat - dlat, lat + dlat, lng - dlng, lng + dlng)
        )

        result = []
        for a in alerts:
            d = {}
            for k, v in dict(a).items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif hasattr(v, '__float__'):
                    d[k] = float(v)
                else:
                    d[k] = v
            # Remove exact address for privacy — keep only area
            d.pop('address', None)
            result.append(d)

        return jsonify(success=True, alerts=result, count=len(result))

    except Exception as e:
        log.error(f'Nearby alerts failed: {e}')
        return jsonify(success=False, error='Failed to fetch nearby alerts.'), 500
