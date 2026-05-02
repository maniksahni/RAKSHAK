import os
import logging

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
from apscheduler.schedulers.background import BackgroundScheduler

from config import config
from models import User, get_db, close_db

log = logging.getLogger('rakshak')

socketio  = SocketIO()
login_manager = LoginManager()
csrf      = CSRFProtect()
limiter   = Limiter(key_func=get_remote_address)
compress  = Compress()
scheduler = BackgroundScheduler(timezone='UTC', daemon=True)


def _acquire_job_lock(lock_name):
    from models import query_db
    row = query_db('SELECT GET_LOCK(%s, 0) AS acquired', (lock_name,), one=True)
    return bool(row and row.get('acquired'))


def _release_job_lock(lock_name):
    try:
        from models import query_db
        query_db('SELECT RELEASE_LOCK(%s) AS released', (lock_name,), one=True)
    except Exception as exc:
        log.warning(f'Failed to release scheduler lock {lock_name}: {exc}')


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
            lock_name = 'rakshak:job:ai_ping_check'
            if not _acquire_job_lock(lock_name):
                logger.info('Scheduler: skipped duplicate missed-ping run')
                return
            try:
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
                            from modules.sos.auto_sos import trigger_auto_sos
                            trigger_auto_sos(u['id'], socketio)

                    except Exception as e:
                        logger.error(f'Scheduler: error processing user {u["id"]}: {e}')
            finally:
                _release_job_lock(lock_name)

    except Exception as e:
        log.error(f'Scheduler job _scheduled_check_missed crashed: {e}')



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
    if config_name == 'production' and not app.config.get('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY must be set in production.')

    # ── Self-healing system (logging, health, error capture) ──────────────
    from healer import init_healer
    init_healer(app)

    # ── Extensions ────────────────────────────────────────────────────────
    # Restrict SocketIO CORS to same origin in production
    cors_origins = (
        os.environ.get('ALLOWED_ORIGINS', '*')
        if config_name == 'development'
        else os.environ.get('ALLOWED_ORIGINS', '')  # production: restrict to configured origin only
    )
    socketio.init_app(
        app,
        async_mode='eventlet',
        cors_allowed_origins=cors_origins,
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25,
    )
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    compress.init_app(app)

    login_manager.login_view    = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # ── DB teardown ───────────────────────────────────────────────────────
    app.teardown_appcontext(close_db)

    # ── Blueprints ────────────────────────────────────────────────────────
    from modules.auth.routes               import auth_bp
    from modules.auth.google_oauth         import google_bp, register_google_oauth
    from modules.sos.routes                import sos_bp, dashboard_bp
    from modules.ai_engine.routes          import ai_bp
    from modules.danger_zones.routes       import danger_bp
    from modules.admin.routes              import admin_bp
    from modules.main.routes               import main_bp
    from modules.safety_tips.routes        import safety_tips_bp
    from modules.emergency.routes          import emergency_bp
    from modules.safe_walk.routes          import safe_walk_bp
    from modules.fake_call.routes          import fake_call_bp
    from modules.safety_score.routes       import safety_score_bp
    from modules.aria_guardian.routes      import aria_guardian_bp
    from modules.guardian_network.routes   import guardian_bp
    from modules.valkyrie.routes           import valkyrie_bp
    from modules.vision_shield.routes     import vision_shield_bp
    from modules.xray_vision.routes       import xray_vision_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,          url_prefix='/auth')
    app.register_blueprint(google_bp)
    app.register_blueprint(sos_bp,           url_prefix='/sos')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ai_bp,            url_prefix='/ai')
    app.register_blueprint(danger_bp,        url_prefix='/danger-zones')
    app.register_blueprint(admin_bp,         url_prefix='/admin')
    app.register_blueprint(safety_tips_bp,   url_prefix='/safety-tips')
    app.register_blueprint(emergency_bp,     url_prefix='/emergency')
    app.register_blueprint(safe_walk_bp,     url_prefix='/safe-walk')
    app.register_blueprint(fake_call_bp,     url_prefix='/fake-call')
    app.register_blueprint(safety_score_bp,  url_prefix='/safety-score')
    app.register_blueprint(aria_guardian_bp, url_prefix='/aria')
    app.register_blueprint(guardian_bp,      url_prefix='/guardian')
    app.register_blueprint(valkyrie_bp,      url_prefix='/valkyrie')
    app.register_blueprint(vision_shield_bp, url_prefix='/vision-shield')
    app.register_blueprint(xray_vision_bp,   url_prefix='/xray-vision')

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
        from flask import redirect, url_for, request as req, jsonify
        path = req.path or ''
        # NEVER redirect these — causes infinite loops:
        # /static/... missing file, /auth/... = login→404→login loop
        if (path.startswith('/static') or path.startswith('/auth') or
                path.startswith('/sos') or path.startswith('/ai') or
                path.startswith('/admin/api') or req.is_json):
            return jsonify(error='Not found'), 404
        return redirect(url_for('auth.login')), 302

    @app.errorhandler(500)
    def internal_error(e):
        """Show an inline error page — never redirect (redirect loops)."""
        from flask import request as req, make_response, jsonify
        log.error(f'500 on {req.path}: {e}')
        path = req.path or ''
        if req.is_json or path.startswith('/sos') or path.startswith('/ai') or path.startswith('/admin/api'):
            return jsonify(error='Internal server error', success=False), 500
        # Render a premium inline error page — NO redirects, which cause loops
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Error — RAKSHAK</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700;900&family=Courier+Prime&display=swap" rel="stylesheet">
  <style>
    *{margin:0;padding:0;box-sizing:border-box;}
    body{background:#060608;color:#fff;font-family:'Space Grotesk',sans-serif;
      display:flex;align-items:center;justify-content:center;min-height:100vh;
      background-image:radial-gradient(ellipse at 50% 50%,rgba(139,92,246,0.05) 0%,transparent 70%);}
    .card{background:rgba(255,255,255,0.03);border:1px solid rgba(139,92,246,0.25);
      border-radius:24px;padding:48px 40px;text-align:center;max-width:480px;
      box-shadow:0 0 60px rgba(139,92,246,0.1),inset 0 1px 0 rgba(255,255,255,0.08);}
    .icon{font-size:3rem;margin-bottom:20px;filter:drop-shadow(0 0 20px rgba(139,92,246,0.6));}
    h1{font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,#fff,#fca5a5);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:12px;}
    p{color:rgba(255,255,255,0.5);font-size:0.9rem;line-height:1.7;margin-bottom:28px;
      font-family:'Courier Prime',monospace;}
    .btns{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;}
    a{padding:12px 28px;border-radius:12px;font-weight:700;font-size:0.88rem;
      text-decoration:none;transition:all 0.3s;display:inline-flex;align-items:center;gap:6px;}
    .btn-primary{background:linear-gradient(135deg,rgba(139,92,246,0.25),rgba(139,92,246,0.1));
      border:1px solid rgba(139,92,246,0.4);color:#c4b5fd;}
    .btn-primary:hover{background:linear-gradient(135deg,rgba(139,92,246,0.4),rgba(139,92,246,0.2));
      transform:translateY(-2px);box-shadow:0 8px 20px rgba(139,92,246,0.3);}
    .btn-secondary{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);color:rgba(255,255,255,0.6);}
    .btn-secondary:hover{border-color:rgba(255,255,255,0.25);color:#fff;transform:translateY(-2px);}
    .code{font-family:'Courier Prime',monospace;font-size:0.7rem;color:rgba(255,255,255,0.2);
      margin-top:28px;letter-spacing:0.15em;}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">⚠️</div>
    <h1>System Anomaly Detected</h1>
    <p>The server encountered an unexpected condition.<br>Our systems have logged this event automatically.</p>
    <div class="btns">
      <a href="javascript:history.back()" class="btn-secondary">← Go Back</a>
      <a href="/dashboard/" class="btn-primary">🛡 Dashboard</a>
      <a href="/auth/login" class="btn-secondary">Login</a>
    </div>
    <div class="code">RAKSHAK · ERROR 500 · AES-256 SECURE</div>
  </div>
</body>
</html>'''
        return make_response(html, 500)


    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import redirect, url_for, flash, request as req, jsonify, make_response
        log.warning(f'Rate limit hit on {req.path}')
        path = req.path or ''
        if req.is_json or path.startswith('/sos') or path.startswith('/ai') or path.startswith('/admin/api'):
            return jsonify(success=False, error='Too many requests. Please slow down.'), 429
        if path.startswith('/auth'):
            return make_response(
                '<html><body style="background:#0a0a0f;color:#ff6b6b;font-family:monospace;'
                'display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">'
                '<div style="text-align:center"><h2>Rate Limited</h2>'
                '<p>Too many requests. Wait a moment then try again.</p>'
                '<a href="/auth/login" style="color:#60a5fa">Try Again</a></div></body></html>', 429)
        flash('Too many requests. Please wait a moment.', 'warning')
        return redirect(url_for('auth.login')), 302


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

        # ── Self-ping keep-alive (prevents Railway idle timeout) ──────────
        keep_alive_url = app.config.get('KEEP_ALIVE_URL', '')
        if keep_alive_url:
            def _keep_alive():
                with _app_ctx():
                    lock_name = 'rakshak:job:keep_alive'
                    if not _acquire_job_lock(lock_name):
                        return
                    try:
                        import requests
                        requests.get(keep_alive_url, timeout=10)
                    except Exception:
                        pass
                    finally:
                        _release_job_lock(lock_name)
            scheduler.add_job(
                _keep_alive,
                trigger='interval',
                seconds=600,  # ping every 10 min to keep Railway alive
                id='keep_alive',
                replace_existing=True,
            )
            log.info(f'Keep-alive pinger started → {keep_alive_url}')

        scheduler.start()
        log.info('APScheduler started — AI ping check every 120s')

    return app


def _auto_init_db(app):
    """Auto-create tables and optional demo seeds on first run."""
    import time
    for attempt in range(10):
        try:
            with app.app_context():
                from models import close_db, query_db
                query_db("SELECT 1 FROM users LIMIT 1")
                log.info('DB tables already exist — skipping init.')
                close_db(None)
                _auto_migrate_guardian(app)
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
        connect_kwargs = dict(
            host=cfg['DB_HOST'], port=cfg['DB_PORT'],
            user=cfg['DB_USER'], password=cfg['DB_PASSWORD'],
            database=cfg['DB_NAME'],
        )
        if cfg.get('DB_SSL'):
            for ca in ['/etc/ssl/certs/ca-certificates.crt', '/etc/ssl/cert.pem']:
                if os.path.exists(ca):
                    connect_kwargs['ssl_ca'] = ca
                    connect_kwargs['ssl_verify_cert'] = True
                    break
            else:
                connect_kwargs['ssl_verify_cert'] = False
            connect_kwargs['ssl_disabled'] = False
        conn = mysql.connector.connect(**connect_kwargs)
        conn.autocommit = True
        cursor = conn.cursor()
        from init_db import SCHEMA_SQL, seed_statements
        for stmt in SCHEMA_SQL:
            cursor.execute(stmt)
        seeds = seed_statements()
        for seed in seeds:
            try:
                cursor.execute(seed)
            except Exception:
                pass
        cursor.close()
        conn.close()
        if seeds:
            log.info('DB init complete — tables created & demo seeds applied.')
        else:
            log.info('DB init complete — tables created without demo seeds.')
    except Exception as e:
        log.error(f'Auto DB init failed: {e}')

    # Run guardian/AI migrations (idempotent — adds columns if missing)
    _auto_migrate_guardian(app)


def _auto_migrate_guardian(app):
    """Add Guardian Angel columns & ai_chat_logs table if they don't exist."""
    USER_COLUMN_MIGRATIONS = [
        ('guardian_active',    'ALTER TABLE users ADD COLUMN guardian_active BOOLEAN DEFAULT FALSE'),
        ('guardian_lat',       'ALTER TABLE users ADD COLUMN guardian_lat DECIMAL(10,8) DEFAULT NULL'),
        ('guardian_lng',       'ALTER TABLE users ADD COLUMN guardian_lng DECIMAL(11,8) DEFAULT NULL'),
        ('guardian_radius_km', 'ALTER TABLE users ADD COLUMN guardian_radius_km DECIMAL(4,2) DEFAULT 1.0'),
        ('guardian_since',     'ALTER TABLE users ADD COLUMN guardian_since TIMESTAMP NULL DEFAULT NULL'),
    ]
    CONTACT_COLUMN_MIGRATIONS = [
        ('notify_email', 'ALTER TABLE trusted_contacts ADD COLUMN notify_email BOOLEAN DEFAULT TRUE'),
        ('notify_phone', 'ALTER TABLE trusted_contacts ADD COLUMN notify_phone BOOLEAN DEFAULT TRUE'),
    ]
    CONTACT_DATA_CLEANUPS = [
        (
            'disable_reserved_email_contacts',
            """UPDATE trusted_contacts
               SET notify_email = FALSE
               WHERE notify_email = TRUE
                 AND (
                    LOWER(TRIM(contact_email)) LIKE '%@%.local'
                    OR LOWER(TRIM(contact_email)) LIKE '%@localhost'
                    OR LOWER(TRIM(contact_email)) LIKE '%@%.localhost'
                    OR LOWER(TRIM(contact_email)) LIKE '%@invalid'
                    OR LOWER(TRIM(contact_email)) LIKE '%@%.invalid'
                    OR LOWER(TRIM(contact_email)) LIKE '%@example.com'
                    OR LOWER(TRIM(contact_email)) LIKE '%@example.org'
                    OR LOWER(TRIM(contact_email)) LIKE '%@example.net'
                 )""",
        ),
    ]
    SOS_COLUMN_MIGRATIONS = [
        ('sos_lat_nullable', "ALTER TABLE sos_alerts MODIFY COLUMN latitude DECIMAL(10,8) NULL DEFAULT NULL"),
        ('sos_lng_nullable', "ALTER TABLE sos_alerts MODIFY COLUMN longitude DECIMAL(11,8) NULL DEFAULT NULL"),
        ('sos_trigger_type_varchar', "ALTER TABLE sos_alerts MODIFY COLUMN trigger_type VARCHAR(32) DEFAULT 'manual'"),
        ('sos_status_varchar', "ALTER TABLE sos_alerts MODIFY COLUMN status VARCHAR(20) DEFAULT 'active'"),
    ]
    TABLE_MIGRATIONS = [
        """CREATE TABLE IF NOT EXISTS ai_chat_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_id VARCHAR(64) NOT NULL,
        role VARCHAR(10) NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]
    try:
        import mysql.connector
        cfg = app.config
        connect_kwargs = dict(
            host=cfg['DB_HOST'], port=cfg['DB_PORT'],
            user=cfg['DB_USER'], password=cfg['DB_PASSWORD'],
            database=cfg['DB_NAME'],
        )
        if cfg.get('DB_SSL'):
            for ca in ['/etc/ssl/certs/ca-certificates.crt', '/etc/ssl/cert.pem']:
                if os.path.exists(ca):
                    connect_kwargs['ssl_ca'] = ca
                    connect_kwargs['ssl_verify_cert'] = True
                    break
            else:
                connect_kwargs['ssl_verify_cert'] = False
            connect_kwargs['ssl_disabled'] = False
        conn = mysql.connector.connect(**connect_kwargs)
        conn.autocommit = True
        cursor = conn.cursor()

        # Column migrations (skip duplicates)
        for col_name, sql in USER_COLUMN_MIGRATIONS + CONTACT_COLUMN_MIGRATIONS:
            try:
                cursor.execute(sql)
                log.info(f'Guardian migration: added column {col_name}')
            except mysql.connector.Error as e:
                if e.errno == 1060:  # Duplicate column
                    pass
                else:
                    log.warning(f'Guardian migration {col_name}: {e}')

        # SOS table compatibility migrations
        for migration_name, sql in SOS_COLUMN_MIGRATIONS:
            try:
                cursor.execute(sql)
                log.info(f'SOS migration applied: {migration_name}')
            except mysql.connector.Error as e:
                log.warning(f'SOS migration {migration_name}: {e}')

        # Disable obviously undeliverable trusted-contact email domains left by old demo data.
        for cleanup_name, sql in CONTACT_DATA_CLEANUPS:
            try:
                cursor.execute(sql)
                if cursor.rowcount:
                    log.info(f'Contact cleanup applied: {cleanup_name} ({cursor.rowcount} row(s))')
            except mysql.connector.Error as e:
                log.warning(f'Contact cleanup {cleanup_name}: {e}')

        # Table migrations
        for sql in TABLE_MIGRATIONS:
            try:
                cursor.execute(sql)
            except Exception:
                pass

        cursor.close()
        conn.close()
        log.info('Guardian migrations complete.')
    except Exception as e:
        log.warning(f'Guardian migration skipped (non-fatal): {e}')


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=False,
                 allow_unsafe_werkzeug=True)
