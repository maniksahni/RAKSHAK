import os

from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config
from models import User, get_db, close_db

socketio = SocketIO()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Extensions
    socketio.init_app(app, async_mode='threading', cors_allowed_origins='*',
                      logger=False, engineio_logger=False,
                      allow_upgrades=False)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # Teardown DB connection
    app.teardown_appcontext(close_db)

    # Register blueprints
    from modules.auth.routes import auth_bp
    from modules.sos.routes import sos_bp, dashboard_bp
    from modules.ai_engine.routes import ai_bp
    from modules.danger_zones.routes import danger_bp
    from modules.admin.routes import admin_bp
    from modules.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sos_bp, url_prefix='/sos')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ai_bp, url_prefix='/ai')
    app.register_blueprint(danger_bp, url_prefix='/danger-zones')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Register socket events
    from socket_events import register_socket_events
    register_socket_events(socketio)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        from flask import render_template
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify
        return jsonify(success=False, error='Too many requests. Please slow down.'), 429

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
