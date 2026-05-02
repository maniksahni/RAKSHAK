from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/health')
def health_check():
    """Primary health check — returns degraded status when dependencies fail."""
    try:
        from healer import build_health_response
        payload, code = build_health_response(strict=True)
        return jsonify(payload), code
    except Exception as e:
        return jsonify(status='unhealthy', error=str(e)), 503


@main_bp.route('/health/strict')
def health_check_strict():
    """Deep health check — returns 503 when the database is degraded."""
    try:
        from healer import build_health_response
        payload, code = build_health_response(strict=True)
        return jsonify(payload), code
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
