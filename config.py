import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'rakshak-dev-secret-key-2024'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Allow GET without CSRF token

    # Database — Railway MySQL (MYSQL* vars) or individual vars
    DB_HOST = os.environ.get('MYSQLHOST') or os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('MYSQLPORT') or os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('MYSQLUSER') or os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('MYSQLPASSWORD') or os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('MYSQLDATABASE') or os.environ.get('DB_NAME', 'rakshak')

    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '20000 per day;5000 per hour'

    # SocketIO
    SOCKETIO_ASYNC_MODE = 'eventlet'


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_SSL_STRICT   = False   # Railway proxy terminates SSL; strict check always fails
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
