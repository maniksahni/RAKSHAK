"""
Google OAuth 2.0 login for RAKSHAK.
Uses authlib for the OAuth flow.

Environment variables required:
  GOOGLE_CLIENT_ID      — from Google Cloud Console
  GOOGLE_CLIENT_SECRET  — from Google Cloud Console
  GOOGLE_ADMIN_EMAILS   — comma-separated list of Gmail addresses that get admin role
                          e.g. maniksahni5@gmail.com,other@gmail.com
"""

import os
import logging
from flask import Blueprint, redirect, url_for, session, request, flash
from flask_login import login_user, current_user
from authlib.integrations.flask_client import OAuth
from models import User, query_db, log_audit
from app import limiter

log = logging.getLogger('rakshak')

google_bp = Blueprint('google_auth', __name__)

# OAuth object — configured per-app in register_google_oauth()
oauth = OAuth()
google = None   # populated after init


def _get_admin_emails():
    """Return set of lowercase emails that should have admin role via Google login."""
    raw = os.environ.get('GOOGLE_ADMIN_EMAILS', '')
    base = set()
    admin_email = (os.environ.get('ADMIN_EMAIL') or '').strip().lower()
    if admin_email:
        base.add(admin_email)
    extras = {e.strip().lower() for e in raw.split(',') if e.strip()}
    return base | extras


def register_google_oauth(app):
    """Call this inside create_app() after the app is created."""
    global google
    oauth.init_app(app)
    google = oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID', ''),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'prompt': 'select_account',   # always show account chooser
        },
    )


# ── Step 1: redirect user to Google ──────────────────────────────────────────
@google_bp.route('/auth/google/login')
@limiter.limit('30 per hour')
def google_login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.index'))

    if not os.environ.get('GOOGLE_CLIENT_ID'):
        flash('Google login is not configured yet.', 'warning')
        return redirect(url_for('auth.login'))

    import secrets
    nonce = secrets.token_urlsafe(16)
    session['google_nonce'] = nonce

    callback_url = url_for('google_auth.google_callback', _external=True, _scheme='https')
    # Fallback: force https if ProxyFix didn't catch it
    if callback_url.startswith('http://') and not os.environ.get('FLASK_DEBUG'):
        callback_url = 'https://' + callback_url[7:]
    log.info(f'Google OAuth redirect_uri: {callback_url}')
    return google.authorize_redirect(callback_url, nonce=nonce)


# ── Step 2: Google redirects back here ───────────────────────────────────────
@google_bp.route('/auth/google/callback')
@limiter.limit('60 per hour')
def google_callback():
    if not os.environ.get('GOOGLE_CLIENT_ID'):
        flash('Google login is not configured.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        token = google.authorize_access_token()
        nonce = session.pop('google_nonce', None)
        # authlib 1.x: userinfo is parsed into token automatically for openid scope
        user_info = token.get('userinfo')
        if user_info is None:
            user_info = google.parse_id_token(token, nonce=nonce)

        google_email = user_info.get('email', '').strip().lower()
        google_name  = user_info.get('name', google_email.split('@')[0])

        if not google_email:
            flash('Could not retrieve your email from Google. Try again.', 'error')
            return redirect(url_for('auth.login'))

        # Determine if this email should be admin
        should_be_admin = google_email in _get_admin_emails()
        role = 'admin' if should_be_admin else 'user'

        # ── Look up user by email ────────────────────────────────────────────
        data = query_db('SELECT * FROM users WHERE email=%s', (google_email,), one=True)

        if data:
            if not data['is_active']:
                flash('Your account has been deactivated. Contact support.', 'error')
                return redirect(url_for('auth.login'))

            # Auto-elevate to admin if email is in admin list
            if should_be_admin and data['role'] != 'admin':
                query_db('UPDATE users SET role=%s WHERE email=%s',
                         ('admin', google_email), commit=True)
                log.info(f'Google login: elevated {google_email} to admin')
                data = query_db('SELECT * FROM users WHERE email=%s',
                                (google_email,), one=True)

            user = User(data)
            login_user(user, remember=True)
            log_audit(user.id, 'google_login', ip_address=request.remote_addr)
            flash(f'Welcome back, {user.full_name.split()[0]}! 👋', 'success')

        else:
            # New user — auto-register with Google, assign correct role
            import secrets as sec
            random_pw = sec.token_urlsafe(32)
            pw_hash   = User.hash_password(random_pw)
            ans_hash  = User.hash_password('google_oauth_user')

            user_id = query_db(
                """INSERT INTO users
                   (full_name, email, phone, password_hash, role,
                    security_question, security_answer_hash, is_active)
                   VALUES (%s, %s, '0000000000', %s, %s,
                           'How did you register?', %s, TRUE)""",
                (google_name, google_email, pw_hash, role, ans_hash),
                commit=True
            )
            log_audit(user_id, 'google_register', 'users', user_id,
                      ip_address=request.remote_addr)

            data = query_db('SELECT * FROM users WHERE id=%s', (user_id,), one=True)
            user = User(data)
            login_user(user, remember=True)
            flash(f'Welcome, {google_name.split()[0]}! 🎉', 'success')

        # Redirect to appropriate dashboard
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.index'))

    except Exception as e:
        import traceback
        log.error(f'Google OAuth callback failed: {e}\n{traceback.format_exc()}')
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))
