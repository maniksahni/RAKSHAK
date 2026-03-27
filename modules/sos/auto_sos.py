"""
Shared auto-SOS trigger logic.
Used by both the AI engine route (request context) and the APScheduler background job.
"""
import logging
from models import query_db, log_audit
from socket_events import emit_sos_alert

log = logging.getLogger('rakshak')


def trigger_auto_sos(user_id, socketio):
    """
    Automatically trigger an SOS alert for an inactive user.

    Parameters
    ----------
    user_id : int
        The user whose heartbeat has been missed.
    socketio : SocketIO
        The SocketIO instance used to broadcast the alert.
    """
    try:
        # Get last known location
        last_ping = query_db(
            """SELECT latitude, longitude FROM ping_logs
               WHERE user_id=%s AND latitude IS NOT NULL AND longitude IS NOT NULL
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,), one=True
        )
        lat = float(last_ping['latitude']) if last_ping else None
        lng = float(last_ping['longitude']) if last_ping else None

        location_note = ''
        if lat is None or lng is None:
            location_note = ' [LOCATION UNAVAILABLE]'

        alert_id = query_db(
            """INSERT INTO sos_alerts
               (user_id, latitude, longitude, trigger_type, message)
               VALUES (%s, %s, %s, 'auto_ai', %s)""",
            (user_id, lat, lng,
             f'Auto-triggered: No heartbeat detected for 6+ minutes{location_note}'),
            commit=True
        )

        query_db(
            "INSERT INTO ping_logs (user_id, ping_type) VALUES (%s, 'auto_sos')",
            (user_id,), commit=True
        )
        log_audit(user_id, 'auto_sos_triggered', 'sos_alerts', alert_id)

        # Notify trusted contacts
        contacts = query_db(
            'SELECT contact_email FROM trusted_contacts WHERE user_id=%s', (user_id,)
        )
        contact_user_ids = []
        for c in (contacts or []):
            cu = query_db('SELECT id FROM users WHERE email=%s',
                          (c['contact_email'],), one=True)
            if cu:
                contact_user_ids.append(cu['id'])

        user_info = query_db('SELECT full_name FROM users WHERE id=%s',
                             (user_id,), one=True)
        name = user_info['full_name'] if user_info else 'User'

        emit_sos_alert(socketio, {
            'id': alert_id, 'user_id': user_id,
            'latitude': lat, 'longitude': lng,
            'trigger_type': 'auto_ai',
            'message': f'AUTO SOS: {name} stopped responding'
        }, contact_user_ids, user_id)

        log.warning(f'Auto-SOS fired for user {user_id} (alert #{alert_id})')

    except Exception as e:
        log.error(f'Auto-SOS failed for user {user_id}: {e}')
