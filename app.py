import os
import logging

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from apscheduler.schedulers.background import BackgroundScheduler

from config import config
from models import User, get_db, close_db

log = logging.getLogger('rakshak')

socketio  = SocketIO()
login_manager = LoginManager()
csrf      = CSRFProtect()
limiter   = Limiter(key_func=get_remote_address)
scheduler = BackgroundScheduler(timezone='UTC', daemon=True)


# ── Scheduled job: AI missed-ping checker ──────────────────────────────────
def _scheduled_check_missed():
    """
    Runs every 2 minutes via APScheduler.
    Checks all active users for missed heartbeats and escalates risk levels.
    Auto-fires SOS if consecutive_missed_pings >= 3.
    """
    try:
        from datetime import datetime, timedelta
        from models import query_db, log_audit
        from socket_events import emit_risk_update, emit_sos_alert
        from healer import logger

        PING_INTERVAL_SEC  = 120
        AUTO_SOS_THRESHOLD = 3

        cutoff = datetime.now() - timedelta(seconds=PING_INTERVAL_SEC + 30)

        with _app_ctx():
            stale_users = query_db(
                """SELECT id, consecutive_missed_pings, full_name, email
                   FROM users
                   WHERE is_active=TRUE AND role='user'
                     AND last_ping IS NOT NULL
                     AND last_ping < %s""",
                (cutoff,)
            )

            for u in stale_users:
                try:
                    missed = u['consecutive_missed_pings'] + 1
                    query_db(
                        'UPDATE users SET consecutive_missed_pings=%s WHERE id=%s',
                        (missed, u['id']), commit=True
                    )
                    query_db(
                        "INSERT INTO ping_logs (user_id, ping_type) VALUES (%s,'missed')",
                        (u['id'],), commit=True
                    )

                    risk = ('high' if missed >= AUTO_SOS_THRESHOLD
                            else 'medium' if missed >= 2 else 'low')
                    query_db('UPDATE users SET risk_level=%s WHERE id=%s',
                             (risk, u['id']), commit=True)
                    emit_risk_update(socketio, u['id'], risk)
                    logger.info(f'User {u["id"]} risk → {risk} (missed={missed})')

                    if missed == AUTO_SOS_THRESHOLD:
                        _trigger_auto_sos_bg(u['id'])

                except Exception as e:
                    logger.error(f'Scheduler: error processing user {u["id"]}: {e}')

    except Exception as e:
        log.error(f'Scheduler job _scheduled_check_missed crashed: {e}')


def _trigger_auto_sos_bg(user_id):
    """Background-safe auto-SOS trigger (no request context needed)."""
    try:
        from models import query_db, log_audit
        from socket_events import emit_sos_alert
        from healer import logger

        last_ping = query_db(
            """SELECT latitude, longitude FROM ping_logs
               WHERE user_id=%s AND latitude IS NOT NULL
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,), one=True
        )
        lat = float(last_ping['latitude'])  if last_ping else 0.0
        lng = float(last_ping['longitude']) if last_ping else 0.0

        alert_id = query_db(
            """INSERT INTO sos_alerts
               (user_id, latitude, longitude, trigger_type, message)
               VALUES (%s, %s, %s, 'auto_ai',
                       'Auto-triggered: No heartbeat detected for 6+ minutes')""",
            (user_id, lat, lng), commit=True
        )
        query_db(
            "INSERT INTO ping_logs (user_id, ping_type) VALUES (%s,'auto_sos')",
            (user_id,), commit=True
        )
        log_audit(user_id, 'auto_sos_triggered', 'sos_alerts', alert_id)

        contacts = query_db(
            'SELECT contact_email FROM trusted_contacts WHERE user_id=%s', (user_id,)
        )
        contact_ids = []
        for c in contacts:
            cu = query_db('SELECT id FROM users WHERE email=%s',
                          (c['contact_email'],), one=True)
            if cu:
                contact_ids.append(cu['id'])

        user_info = query_db('SELECT full_name FROM users WHERE id=%s',
                             (user_id,), one=True)
        name = user_info['full_name'] if user_info else 'User'

        emit_sos_alert(socketio, {
            'id': alert_id, 'user_id': user_id,
            'latitude': lat, 'longitude': lng,
            'trigger_type': 'auto_ai',
            'message': f'AUTO SOS: {name} stopped responding'
        }, contact_ids, user_id)

        logger.warning(f'Auto-SOS fired for user {user_id} (alert #{alert_id})')

    except Exception as e:
        log.error(f'Auto-SOS failed for user {user_id}: {e}')


# App context manager for background jobs
_flask_app = None

def _app_ctx():
    """Return a Flask app context for background threads."""
    return _flask_app.app_context()





# ── App Factory ────────────────────────────────────────────────────────────
def create_app(config_name=None):
    global _flask_app

    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.from_object(config[config_name])
    _flask_app = app

    # ── Self-healing system (logging, health, error capture) ──────────────
    from healer import init_healer
    init_healer(app)

    # ── Extensions ────────────────────────────────────────────────────────
    # Restrict SocketIO CORS to same origin in production
    cors_origins = (
        os.environ.get('ALLOWED_ORIGINS', '*')
        if config_name == 'development'
        else os.environ.get('ALLOWED_ORIGINS', '*')
    )
    socketio.init_app(
        app,
        async_mode='eventlet',
        cors_allowed_origins=cors_origins,
        logger=False,
        engineio_logger=False,
        allow_upgrades=False,
        ping_timeout=60,
        ping_interval=25,
    )
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view    = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # ── DB teardown ───────────────────────────────────────────────────────
    app.teardown_appcontext(close_db)

    # ── Blueprints ────────────────────────────────────────────────────────
    from modules.auth.routes          import auth_bp
    from modules.auth.google_oauth    import google_bp, register_google_oauth
    from modules.sos.routes           import sos_bp, dashboard_bp
    from modules.ai_engine.routes     import ai_bp
    from modules.danger_zones.routes  import danger_bp
    from modules.admin.routes         import admin_bp
    from modules.main.routes          import main_bp
    from modules.safety_tips.routes   import safety_tips_bp
    from modules.emergency.routes     import emergency_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(google_bp)
    app.register_blueprint(sos_bp,       url_prefix='/sos')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ai_bp,        url_prefix='/ai')
    app.register_blueprint(danger_bp,    url_prefix='/danger-zones')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(safety_tips_bp, url_prefix='/safety-tips')
    app.register_blueprint(emergency_bp,   url_prefix='/emergency')

    # ── Google OAuth ──────────────────────────────────────────────────────
    register_google_oauth(app)

    # ── Socket events ─────────────────────────────────────────────────────
    from socket_events import register_socket_events
    register_socket_events(socketio)



    # ── Global Jinja2 helpers ─────────────────────────────────────────────────
    def _fmt_dt(value, fmt='%d %b %Y %H:%M'):
        """Safe date formatter: works with datetime objects, ISO strings, or None."""
        if not value:
            return ''
        try:
            from datetime import datetime
            if hasattr(value, 'strftime'):
                return value.strftime(fmt)
            # ISO string: "2026-03-21T13:25:53" or "2026-03-21 13:25:53"
            s = str(value).replace('T', ' ').split('.')[0]
            return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').strftime(fmt)
        except Exception:
            return str(value)[:16]  # fallback: return raw string slice

    app.jinja_env.filters['fmt_dt'] = _fmt_dt

    # ── HTTP Error handlers ───────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        """Never show a crash page — redirect back or to login."""
        from flask import redirect, url_for, flash, request as req
        log.error(f'500 on {req.path}: {e}')
        try:
            flash('Something went wrong on that page. Please try again.', 'warning')
            # Go back to previous page if available and different from crashed page
            referrer = req.referrer
            if referrer and req.path and req.path not in referrer:
                return redirect(referrer), 302
            # Safe fallback: login page (always works, no auth required)
            return redirect(url_for('auth.login')), 302
        except Exception:
            from flask import render_template
            return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify
        return jsonify(success=False, error='Too many requests. Please slow down.'), 429

    # ── Auto-init DB tables on first run ─────────────────────────────────
    _auto_init_db(app)

    # ── APScheduler — start background AI checks ─────────────────────────
    if not scheduler.running:
        scheduler.add_job(
            _scheduled_check_missed,
            trigger='interval',
            seconds=120,
            id='ai_ping_check',
            replace_existing=True,
            misfire_grace_time=30,
        )
        scheduler.start()
        log.info('APScheduler started — AI ping check every 120s')

    return app


def _auto_init_db(app):
    """Auto-create tables & seed admin if DB is empty (Railway/Docker first-run)."""
    import time
    for attempt in range(10):
        try:
            with app.app_context():
                from models import query_db
                query_db("SELECT 1 FROM users LIMIT 1")
                log.info('DB tables already exist — skipping init.')
                return
        except Exception as e:
            err = str(e)
            if 'does not exist' in err or 'relation' in err:
                break  # tables missing, run init
            log.warning(f'DB not ready (attempt {attempt+1}/10): {e}')
            time.sleep(3)

    log.info('Initialising database tables...')
    try:
        import mysql.connector
        cfg = app.config
        conn = mysql.connector.connect(
            host=cfg['DB_HOST'], port=cfg['DB_PORT'],
            user=cfg['DB_USER'], password=cfg['DB_PASSWORD'],
            database=cfg['DB_NAME'],
        )
        conn.autocommit = True
        cursor = conn.cursor()
        from init_db import SCHEMA_SQL, SEEDS
        for stmt in SCHEMA_SQL:
            cursor.execute(stmt)
        for seed in SEEDS:
            try:
                cursor.execute(seed)
            except Exception:
                pass
        cursor.close()
        conn.close()
        log.info('DB init complete — tables created & admin seeded.')
    except Exception as e:
        log.error(f'Auto DB init failed: {e}')


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=False,
                 allow_unsafe_werkzeug=True)
