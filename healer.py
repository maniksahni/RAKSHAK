"""
RAKSHAK Self-Healing System
============================
Handles:
  - Centralized structured logging (rotating file + console)
  - DB connection auto-retry with exponential backoff
  - Health checks for every critical system
  - Request-level error capture
  - Graceful degradation on partial failures

Import and call `init_healer(app)` inside create_app().
"""

import os
import time
import logging
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

from flask import jsonify, request, g


# ═══════════════════════════════════════════
#  LOGGING SETUP
# ═══════════════════════════════════════════

LOG_DIR  = os.path.join(os.path.dirname(__file__), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'rakshak.log')

def _setup_logging():
    """Configure rotating file + console logger for the whole app."""
    os.makedirs(LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Rotating file — 5 MB × 3 backups
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setLevel(logging.WARNING)
    fh.setFormatter(fmt)

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(fh)
        root.addHandler(ch)

    return logging.getLogger('rakshak')


logger = _setup_logging()


# ═══════════════════════════════════════════
#  DB RETRY WRAPPER
# ═══════════════════════════════════════════

def db_retry(fn, *args, retries=3, delay=0.5, **kwargs):
    """
    Execute a DB function with automatic retry on connection errors.
    Uses exponential backoff: delay, delay*2, delay*4 ...
    """
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            # Only retry on transient connection errors
            is_transient = any(kw in err_str for kw in [
                'connection', 'lost', 'gone away', 'timeout',
                'pool', 'reset', 'broken pipe', '2006', '2013'
            ])
            if not is_transient or attempt == retries:
                break
            wait = delay * (2 ** (attempt - 1))
            logger.warning(
                f'DB transient error (attempt {attempt}/{retries}), '
                f'retrying in {wait:.1f}s: {e}'
            )
            time.sleep(wait)
            # Force fresh connection on next attempt
            try:
                from flask import g as flask_g
                db = flask_g.pop('db', None)
                if db and db.is_connected():
                    db.close()
            except Exception:
                pass

    logger.error(f'DB operation failed after {retries} attempts: {last_err}')
    raise last_err


# ═══════════════════════════════════════════
#  HEALTH CHECKS
# ═══════════════════════════════════════════

def _check_db():
    """Ping the database and return (ok: bool, latency_ms: float)."""
    try:
        from models import query_db
        t0 = time.monotonic()
        query_db("SELECT 1", one=True)
        ms = round((time.monotonic() - t0) * 1000, 2)
        return True, ms
    except Exception as e:
        logger.error(f'Health-check DB failure: {e}')
        return False, -1


def _check_scheduler():
    """Return True if APScheduler is running."""
    try:
        from app import scheduler
        return scheduler.running, None
    except Exception:
        return False, None


def build_health_response():
    """Build the full health payload."""
    db_ok, db_ms = _check_db()
    sched_ok, _  = _check_scheduler()

    status = 'healthy' if db_ok else 'degraded'
    code   = 200       if db_ok else 503

    payload = {
        'status':    status,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version':   '3.0',
        'checks': {
            'database':  {'ok': db_ok,   'latency_ms': db_ms},
            'scheduler': {'ok': sched_ok},
        }
    }
    return payload, code


# ═══════════════════════════════════════════
#  INPUT SANITISATION HELPERS
# ═══════════════════════════════════════════

def validate_coords(lat, lng):
    """Return (lat, lng) as floats or raise ValueError."""
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        raise ValueError('Latitude and longitude must be numeric.')
    if not (-90 <= lat <= 90):
        raise ValueError(f'Latitude {lat} out of range [-90, 90].')
    if not (-180 <= lng <= 180):
        raise ValueError(f'Longitude {lng} out of range [-180, 180].')
    return lat, lng


def validate_battery(value):
    """Return battery level clamped to [0, 100] or None."""
    if value is None:
        return None
    try:
        v = float(value)
        return max(0.0, min(100.0, v))
    except (TypeError, ValueError):
        return None


def sanitize_str(value, max_len=500):
    """Strip and truncate a string field."""
    if value is None:
        return ''
    return str(value).strip()[:max_len]


# ═══════════════════════════════════════════
#  FLASK INTEGRATION
# ═══════════════════════════════════════════

def init_healer(app):
    """
    Attach all self-healing capabilities to a Flask app.
    Call this once inside create_app().
    """

    # ── /ping (Railway uptime check) ──────
    # NOTE: /health is registered in modules/main/routes.py
    @app.route('/ping')
    def ping_alive():
        return jsonify(ok=True, ts=datetime.utcnow().isoformat()), 200

    # ── Request timing ────────────────────
    @app.before_request
    def _start_timer():
        g._req_start = time.monotonic()

    @app.after_request
    def _log_request(response):
        try:
            duration = round((time.monotonic() - g._req_start) * 1000, 1)
            if response.status_code >= 500:
                logger.error(
                    f'{request.method} {request.path} → {response.status_code} '
                    f'({duration}ms) ip={request.remote_addr}'
                )
            elif duration > 2000:
                logger.warning(
                    f'SLOW {request.method} {request.path} → {response.status_code} '
                    f'({duration}ms)'
                )
        except Exception:
            pass
        return response

    # ── Unhandled exception capture ───────
    @app.errorhandler(Exception)
    def _unhandled(e):
        # Don't intercept HTTP exceptions (werkzeug)
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e

        tb = traceback.format_exc()
        logger.error(
            f'Unhandled exception on {request.method} {request.path}\n{tb}'
        )

        # Return JSON for API paths, HTML for page paths
        if (request.path.startswith('/sos') or
                request.path.startswith('/ai') or
                request.path.startswith('/danger') or
                request.path.startswith('/admin') and
                request.headers.get('X-Requested-With') == 'XMLHttpRequest'):
            return jsonify(
                success=False,
                error='An internal error occurred. Our system has logged it.'
            ), 500

        # Inline error page — avoids TemplateNotFound if errors/500.html is missing
        html = '''<!DOCTYPE html><html><head><title>Error — RAKSHAK</title>
        <style>body{background:#060608;color:#fff;font-family:sans-serif;
        display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
        .box{text-align:center;padding:40px;}</style></head>
        <body><div class="box"><h1>&#9888;&#65039; Internal Error</h1>
        <p>Something went wrong. Please try again.</p>
        <a href="/" style="color:#c4b5fd">Go Home</a></div></body></html>'''
        from flask import make_response
        return make_response(html, 500)

    logger.info('RAKSHAK self-healing system initialised.')
