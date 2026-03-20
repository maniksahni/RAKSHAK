import time
import logging
import mysql.connector
from mysql.connector import pooling
from flask import current_app, g
from flask_login import UserMixin
import bcrypt

log = logging.getLogger('rakshak')

# ─── Connection Pool ──────────────────────────────────────────────────────────

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        cfg = current_app.config
        _pool = pooling.MySQLConnectionPool(
            pool_name="rakshak_pool",
            pool_size=5,
            host=cfg['DB_HOST'],
            port=cfg['DB_PORT'],
            user=cfg['DB_USER'],
            password=cfg['DB_PASSWORD'],
            database=cfg['DB_NAME'],
            charset='utf8mb4',
            autocommit=False,
            connection_timeout=10,
        )
    return _pool


def _fresh_connection():
    """Force a new connection bypassing pool cache."""
    global _pool
    _pool = None          # reset pool so next call rebuilds
    return get_pool().get_connection()


def get_db():
    if 'db' not in g:
        try:
            g.db = get_pool().get_connection()
        except Exception as e:
            log.error(f'DB pool exhausted or connection failed: {e}')
            raise
    else:
        # Ping existing connection — heal if broken
        try:
            if not g.db.is_connected():
                g.db.reconnect(attempts=3, delay=0.5)
        except Exception:
            try:
                g.db = _fresh_connection()
            except Exception as e:
                log.error(f'DB reconnect failed: {e}')
                raise
    return g.db


def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            if db.is_connected():
                db.close()
        except Exception:
            pass


def query_db(query, args=(), one=False, commit=False, _retries=2):
    """
    Execute a parameterized query with automatic retry on transient errors.
    Returns list of dicts, single dict, or lastrowid on commit.
    """
    last_err = None
    for attempt in range(1, _retries + 2):
        conn = None
        cursor = None
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, args)
            if commit:
                conn.commit()
                return cursor.lastrowid
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv

        except mysql.connector.errors.OperationalError as e:
            last_err = e
            err_code = e.errno if hasattr(e, 'errno') else 0
            # 2006 = server gone away, 2013 = lost connection
            if err_code in (2006, 2013) and attempt <= _retries:
                log.warning(f'DB OperationalError {err_code}, retrying (attempt {attempt})...')
                try:
                    g.pop('db', None)          # force fresh connection next get_db()
                except Exception:
                    pass
                time.sleep(0.5 * attempt)
                continue
            if commit and conn:
                try: conn.rollback()
                except Exception: pass
            raise

        except Exception as e:
            last_err = e
            if commit and conn:
                try: conn.rollback()
                except Exception: pass
            raise

        finally:
            if cursor:
                try: cursor.close()
                except Exception: pass

    raise last_err


# ─── User Model for Flask-Login ───────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, data: dict):
        self.id          = data['id']
        self.full_name   = data['full_name']
        self.email       = data['email']
        self.phone       = data['phone']
        self.role        = data['role']
        self.risk_level  = data.get('risk_level', 'low')
        self.is_active   = data.get('is_active', True)
        self.last_ping   = data.get('last_ping')
        self.consecutive_missed_pings = data.get('consecutive_missed_pings', 0)
        self.address     = data.get('address', '')
        self.profile_image = data.get('profile_image', '')
        self.created_at  = data.get('created_at')

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_user(self):
        return self.role == 'user'

    @staticmethod
    def get_by_id(user_id):
        try:
            data = query_db(
                "SELECT * FROM users WHERE id = %s AND is_active = TRUE",
                (user_id,), one=True
            )
            return User(data) if data else None
        except Exception as e:
            log.error(f'User.get_by_id({user_id}) failed: {e}')
            return None

    @staticmethod
    def get_by_email(email):
        try:
            data = query_db(
                "SELECT * FROM users WHERE email = %s AND is_active = TRUE",
                (email,), one=True
            )
            return User(data) if data else None
        except Exception as e:
            log.error(f'User.get_by_email failed: {e}')
            return None

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def check_password(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False


def log_audit(user_id, action, table_name=None, record_id=None,
              old_value=None, new_value=None, ip_address=None, user_agent=None):
    """Insert an audit log entry — never raises, logs failures."""
    import json
    try:
        query_db(
            """INSERT INTO audit_logs
               (user_id, action, table_name, record_id, old_value, new_value, ip_address, user_agent)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, action, table_name, record_id,
             json.dumps(old_value) if old_value else None,
             json.dumps(new_value) if new_value else None,
             ip_address, user_agent),
            commit=True
        )
    except Exception as e:
        log.warning(f'Audit log failed (action={action}, user={user_id}): {e}')
