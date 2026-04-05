import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rakshak-dev-secret-key-2024'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Allow GET without CSRF token

    # Database — supports Railway, Aiven, any MySQL provider
    DB_HOST = os.environ.get('MYSQLHOST') or os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('MYSQLPORT') or os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('MYSQLUSER') or os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('MYSQLPASSWORD') or os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('MYSQLDATABASE') or os.environ.get('DB_NAME', 'rakshak')
    DB_SSL = os.environ.get('DB_SSL', 'false').lower() in ('true', '1', 'yes')
    DB_SSL_CA = os.environ.get('DB_SSL_CA', '/etc/ssl/cert.pem')  # TiDB default CA path

    # Self-ping keep-alive (prevents free-tier sleep)
    KEEP_ALIVE_URL = os.environ.get('KEEP_ALIVE_URL', '')  # e.g. https://rakshak.onrender.com/health

    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '100000 per day;10000 per hour'

    # SocketIO
    SOCKETIO_ASYNC_MODE = 'eventlet'


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_SSL_STRICT   = False   # Render proxy terminates SSL; strict check always fails
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
