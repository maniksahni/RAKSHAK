from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import query_db, log_audit
from socket_events import emit_danger_zone
from datetime import datetime, timedelta
from functools import wraps

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify(success=False, error='Admin access required.'), 403
        return f(*args, **kwargs)
    return decorated


def get_socketio():
    from app import socketio
    return socketio


# ── Admin Dashboard ───────────────────────────────────────────────────────────
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Summary stats
    total_users   = query_db("SELECT COUNT(*) as cnt FROM users WHERE role='user'", one=True)
    total_alerts  = query_db('SELECT COUNT(*) as cnt FROM sos_alerts', one=True)
    active_alerts = query_db("SELECT COUNT(*) as cnt FROM sos_alerts WHERE status='active'", one=True)
    pending_zones = query_db("SELECT COUNT(*) as cnt FROM danger_zones WHERE status='pending'", one=True)
    high_risk     = query_db("SELECT COUNT(*) as cnt FROM users WHERE risk_level='high' AND role='user'", one=True)

    # Recent SOS alerts for map
    recent_alerts = query_db(
        """SELECT sa.*, u.full_name, u.phone
           FROM sos_alerts sa JOIN users u ON sa.user_id=u.id
           ORDER BY sa.created_at DESC LIMIT 50"""
    )
    # Approved danger zones for map
    danger_zones = query_db(
        "SELECT * FROM danger_zones WHERE status='approved' ORDER BY created_at DESC LIMIT 100"
    )

    def _safe_rows(rows):
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

    stats = {
        'total_users':   total_users['cnt'] if total_users else 0,
        'total_alerts':  total_alerts['cnt'] if total_alerts else 0,
        'active_alerts': active_alerts['cnt'] if active_alerts else 0,
        'pending_zones': pending_zones['cnt'] if pending_zones else 0,
        'high_risk':     high_risk['cnt'] if high_risk else 0,
    }
    return render_template('admin/dashboard.html', stats=stats,
                           recent_alerts=_safe_rows(recent_alerts),
                           danger_zones=_safe_rows(danger_zones),
                           now=datetime.utcnow().strftime('%Y-%m-%d %H:%M'))


# ── Analytics ─────────────────────────────────────────────────────────────────
@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    try:
        # Alerts per day (last 14 days)
        alerts_per_day = query_db(
            """SELECT DATE(created_at) as date, COUNT(*) as count
               FROM sos_alerts
               WHERE created_at >= NOW() - INTERVAL 14 DAY
               GROUP BY DATE(created_at)
               ORDER BY date ASC"""
        )

        # Peak hours distribution
        peak_hours = query_db(
            """SELECT HOUR(created_at) as hour, COUNT(*) as count
               FROM sos_alerts GROUP BY HOUR(created_at) ORDER BY hour LIMIT 24"""
        )

        # Risk level distribution
        risk_dist = query_db(
            """SELECT risk_level, COUNT(*) as count
               FROM users WHERE role='user' AND is_active=TRUE
               GROUP BY risk_level LIMIT 50"""
        )

        # Alert status distribution
        alert_status = query_db(
            """SELECT status, COUNT(*) as count FROM sos_alerts GROUP BY status LIMIT 50"""
        )

        # Zone type distribution
        zone_types = query_db(
            """SELECT zone_type, COUNT(*) as count
               FROM danger_zones WHERE status='approved' GROUP BY zone_type LIMIT 50"""
        )

        def serialize(rows):
            result = []
            for r in rows:
                d = {}
                for k, v in r.items():
                    d[k] = v.isoformat() if hasattr(v, 'isoformat') else v
                result.append(d)
            return result

        return jsonify(success=True,
                       alerts_per_day=serialize(alerts_per_day),
                       peak_hours=serialize(peak_hours),
                       risk_dist=serialize(risk_dist),
                       alert_status=serialize(alert_status),
                       zone_types=serialize(zone_types))

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── User Management ───────────────────────────────────────────────────────────
@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    try:
        page     = int(request.args.get('page', 1))
        per_page = 20
        offset   = (page - 1) * per_page
        search   = request.args.get('q', '').strip()

        if search:
            users = query_db(
                """SELECT id, full_name, email, phone, role, risk_level,
                          is_active, created_at, last_ping
                   FROM users WHERE (full_name LIKE %s OR email LIKE %s)
                   ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (f'%{search}%', f'%{search}%', per_page, offset)
            )
        else:
            users = query_db(
                """SELECT id, full_name, email, phone, role, risk_level,
                          is_active, created_at, last_ping
                   FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (per_page, offset)
            )

        result = []
        for u in users:
            d = dict(u)
            for k in ['created_at', 'last_ping']:
                if d.get(k) and hasattr(d[k], 'isoformat'):
                    d[k] = d[k].isoformat()
            result.append(d)
        return jsonify(success=True, users=result)

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@admin_bp.route('/users/<int:uid>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(uid):
    try:
        if uid == current_user.id:
            return jsonify(success=False, error='Cannot deactivate yourself.'), 400
        u = query_db('SELECT is_active FROM users WHERE id=%s', (uid,), one=True)
        if not u:
            return jsonify(success=False, error='User not found.'), 404
        new_status = not u['is_active']
        query_db('UPDATE users SET is_active=%s WHERE id=%s', (new_status, uid), commit=True)
        log_audit(current_user.id, 'toggle_user', 'users', uid,
                  new_value={'is_active': new_status}, ip_address=request.remote_addr)
        return jsonify(success=True, is_active=new_status)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@admin_bp.route('/users/<int:uid>/change-role', methods=['POST'])
@login_required
@admin_required
def change_role(uid):
    try:
        new_role = request.get_json().get('role')
        if new_role not in ['user', 'trusted_contact', 'admin']:
            return jsonify(success=False, error='Invalid role.'), 400
        query_db('UPDATE users SET role=%s WHERE id=%s', (new_role, uid), commit=True)
        log_audit(current_user.id, 'change_role', 'users', uid,
                  new_value={'role': new_role}, ip_address=request.remote_addr)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Danger Zone Approvals ─────────────────────────────────────────────────────
@admin_bp.route('/danger-zones/pending')
@login_required
@admin_required
def pending_zones():
    try:
        zones = query_db(
            """SELECT dz.*, u.full_name as reporter_name, u.email as reporter_email
               FROM danger_zones dz JOIN users u ON dz.reported_by=u.id
               WHERE dz.status='pending' ORDER BY dz.created_at DESC LIMIT 100"""
        )
        result = []
        for z in zones:
            d = dict(z)
            for k in ['created_at', 'approved_at']:
                if d.get(k) and hasattr(d[k], 'isoformat'):
                    d[k] = d[k].isoformat()
            result.append(d)
        return jsonify(success=True, zones=result)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@admin_bp.route('/danger-zones/<int:zone_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_zone(zone_id):
    try:
        query_db(
            """UPDATE danger_zones SET status='approved',
               approved_by=%s, approved_at=%s WHERE id=%s""",
            (current_user.id, datetime.now(), zone_id), commit=True
        )
        zone = query_db('SELECT * FROM danger_zones WHERE id=%s', (zone_id,), one=True)
        if zone:
            zone_dict = {k: (v.isoformat() if hasattr(v, 'isoformat') else v)
                         for k, v in dict(zone).items()}
            emit_danger_zone(get_socketio(), zone_dict)
        log_audit(current_user.id, 'approve_zone', 'danger_zones', zone_id,
                  ip_address=request.remote_addr)
        return jsonify(success=True, message='Danger zone approved.')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@admin_bp.route('/danger-zones/<int:zone_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_zone(zone_id):
    try:
        query_db("UPDATE danger_zones SET status='rejected' WHERE id=%s", (zone_id,), commit=True)
        log_audit(current_user.id, 'reject_zone', 'danger_zones', zone_id,
                  ip_address=request.remote_addr)
        return jsonify(success=True, message='Danger zone rejected.')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Live Alert Feed ───────────────────────────────────────────────────────────
@admin_bp.route('/alerts-feed')
@login_required
@admin_required
def alerts_feed():
    try:
        alerts = query_db(
            """SELECT sa.id, sa.user_id, sa.latitude, sa.longitude, sa.address,
                      sa.trigger_type, sa.status, sa.created_at,
                      u.full_name, u.phone, u.risk_level
               FROM sos_alerts sa JOIN users u ON sa.user_id=u.id
               ORDER BY sa.created_at DESC LIMIT 50"""
        )
        result = [{k: (v.isoformat() if hasattr(v, 'isoformat') else v)
                   for k, v in dict(a).items()} for a in alerts]
        return jsonify(success=True, alerts=result)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Resolve alert (admin) ─────────────────────────────────────────────────────
@admin_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_alert(alert_id):
    try:
        query_db(
            "UPDATE sos_alerts SET status='resolved', resolved_at=%s WHERE id=%s",
            (datetime.now(), alert_id), commit=True
        )
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Audit Logs ────────────────────────────────────────────────────────────────
@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    try:
        logs = query_db(
            """SELECT al.*, u.full_name, u.email
               FROM audit_logs al
               LEFT JOIN users u ON al.user_id=u.id
               ORDER BY al.created_at DESC LIMIT 100"""
        )
        result = [{k: (v.isoformat() if hasattr(v, 'isoformat') else v)
                   for k, v in dict(l).items()} for l in logs]
        return jsonify(success=True, logs=result)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
