import logging
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from flask import request

log = logging.getLogger('rakshak')


def register_socket_events(socketio):

    @socketio.on('connect')
    def handle_connect():
        try:
            if current_user.is_authenticated:
                join_room(f'user_{current_user.id}')
                join_room(f'role_{current_user.role}')
                emit('connected', {
                    'status': 'connected',
                    'user_id': current_user.id,
                    'role': current_user.role
                })
        except Exception as e:
            log.error(f'Socket connect error: {e}')

    @socketio.on('disconnect')
    def handle_disconnect():
        try:
            if current_user.is_authenticated:
                leave_room(f'user_{current_user.id}')
                leave_room(f'role_{current_user.role}')
        except Exception as e:
            log.error(f'Socket disconnect error: {e}')

    @socketio.on('join_admin')
    def handle_join_admin():
        try:
            if current_user.is_authenticated and current_user.is_admin:
                join_room('admin_room')
                emit('joined_admin', {'status': 'ok'})
        except Exception as e:
            log.error(f'Socket join_admin error: {e}')

    @socketio.on('ping_alive')
    def handle_ping(data):
        """Client sends ping to indicate they're active."""
        try:
            if not current_user.is_authenticated:
                emit('ping_ack', {'status': 'error', 'message': 'Not authenticated'})
                return
            from models import query_db
            from datetime import datetime
            lat = data.get('lat') if isinstance(data, dict) else None
            lng = data.get('lng') if isinstance(data, dict) else None
            query_db(
                """UPDATE users SET last_ping=%s, consecutive_missed_pings=0 WHERE id=%s""",
                (datetime.now(), current_user.id), commit=True
            )
            query_db(
                """INSERT INTO ping_logs (user_id, ping_type, latitude, longitude)
                   VALUES (%s, 'heartbeat', %s, %s)""",
                (current_user.id, lat, lng), commit=True
            )
            emit('ping_ack', {'status': 'ok', 'timestamp': datetime.now().isoformat()})
        except Exception as e:
            log.error(f'Socket ping_alive error for user {getattr(current_user, "id", "?")}: {e}')
            emit('ping_ack', {'status': 'error', 'message': 'Internal server error'})


def emit_sos_alert(socketio, alert_data, trusted_contact_ids, user_id):
    """Broadcast SOS alert to all trusted contacts and admins."""
    payload = {
        'type': 'sos_alert',
        'alert': alert_data
    }
    # Notify each trusted contact
    for contact_id in trusted_contact_ids:
        socketio.emit('new_alert', payload, room=f'user_{contact_id}')

    # Notify all admins
    socketio.emit('new_sos', payload, room='role_admin')
    socketio.emit('new_sos', payload, room='admin_room')


def emit_risk_update(socketio, user_id, risk_level):
    """Push risk level update to admin dashboard."""
    socketio.emit('risk_update', {
        'user_id': user_id,
        'risk_level': risk_level
    }, room='admin_room')


def emit_danger_zone(socketio, zone_data):
    """Broadcast new approved danger zone to all users."""
    socketio.emit('new_danger_zone', {'zone': zone_data}, broadcast=True)
