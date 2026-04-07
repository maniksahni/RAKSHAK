import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rakshak-dev-secret-key-2024'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Allow GET without CSRF token

    # Database — TiDB Cloud / any MySQL provider (also supports Railway native env vars)
    DB_HOST = os.environ.get('MYSQLHOST', os.environ.get('DB_HOST', 'localhost'))
    DB_PORT = int(os.environ.get('MYSQLPORT', os.environ.get('DB_PORT', 3306)))
    DB_USER = os.environ.get('MYSQLUSER', os.environ.get('DB_USER', 'root'))
    DB_PASSWORD = os.environ.get('MYSQLPASSWORD', os.environ.get('DB_PASSWORD', ''))
    DB_NAME = os.environ.get('MYSQLDATABASE', os.environ.get('DB_NAME', 'rakshak'))
    DB_SSL = os.environ.get('DB_SSL', 'false').lower() in ('true', '1', 'yes')
    DB_SSL_CA = os.environ.get('DB_SSL_CA', '/etc/ssl/cert.pem')  # TiDB default CA path

    # Self-ping keep-alive (prevents free-tier sleep)
    KEEP_ALIVE_URL = os.environ.get('KEEP_ALIVE_URL', '')  # e.g. https://rakshak.up.railway.app/health

    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '100000 per day;10000 per hour'

    # SocketIO
    SOCKETIO_ASYNC_MODE = 'eventlet'


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    PREFERRED_URL_SCHEME    = 'https'
    WTF_CSRF_SSL_STRICT   = False   # Railway proxy terminates SSL; strict check always fails
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # ── Performance: gzip compression ─────────────────────────────────────
    COMPRESS_REGISTER  = True
    COMPRESS_MIMETYPES = [
        'text/html', 'text/css', 'text/javascript',
        'application/javascript', 'application/json',
        'image/svg+xml',
    ]
    COMPRESS_LEVEL     = 6   # balanced speed/ratio
    COMPRESS_MIN_SIZE  = 500 # bytes — don't compress tiny responses

    # ── Performance: static asset browser caching (1 week) ───────────────
    SEND_FILE_MAX_AGE_DEFAULT = 604800  # 7 days in seconds


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
