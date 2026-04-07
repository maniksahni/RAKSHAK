from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/health')
def health_check():
    """Health check — used by Docker, Railway, any platform."""
    try:
        from models import query_db
        query_db('SELECT 1', one=True)
        return jsonify(status='healthy', service='RAKSHAK'), 200
    except Exception as e:
        return jsonify(status='unhealthy', error=str(e)), 503


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.index'))
    return render_template('index.html')


@main_bp.route('/offline')
def offline():
    """Offline fallback page for service worker."""
    return render_template('offline.html')


@main_bp.route('/dashboard')
def dashboard_redirect():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return redirect(url_for('dashboard.index'))
