"""
Google OAuth 2.0 login for RAKSHAK.
Uses authlib for the OAuth flow.

Environment variables required:
  GOOGLE_CLIENT_ID     — from Google Cloud Console
  GOOGLE_CLIENT_SECRET — from Google Cloud Console
"""

import os
import logging
from flask import Blueprint, redirect, url_for, session, request, flash
from flask_login import login_user, current_user
from authlib.integrations.flask_client import OAuth
from models import User, query_db, log_audit

log = logging.getLogger('rakshak')

google_bp = Blueprint('google_auth', __name__)

# OAuth object — configured per-app in register_google_oauth()
oauth = OAuth()
google = None   # populated after init


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
def google_login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.index'))

    if not os.environ.get('GOOGLE_CLIENT_ID'):
        flash('Google login is not configured yet.', 'warning')
        return redirect(url_for('auth.login'))

    # nonce prevents replay attacks
    import secrets
    nonce = secrets.token_urlsafe(16)
    session['google_nonce'] = nonce

    callback_url = url_for('google_auth.google_callback', _external=True)
    return google.authorize_redirect(callback_url, nonce=nonce)


# ── Step 2: Google redirects back here ───────────────────────────────────────
@google_bp.route('/auth/google/callback')
def google_callback():
    if not os.environ.get('GOOGLE_CLIENT_ID'):
        flash('Google login is not configured.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        token = google.authorize_access_token()
        nonce = session.pop('google_nonce', None)
        user_info = google.parse_id_token(token, nonce=nonce)

        google_email = user_info.get('email', '').strip().lower()
        google_name  = user_info.get('name', google_email.split('@')[0])

        if not google_email:
            flash('Could not retrieve your email from Google. Try again.', 'error')
            return redirect(url_for('auth.login'))

        # ── Look up user by email ────────────────────────────────────────────
        data = query_db('SELECT * FROM users WHERE email=%s', (google_email,), one=True)

        if data:
            # Existing user — check if active
            if not data['is_active']:
                flash('Your account has been deactivated. Contact support.', 'error')
                return redirect(url_for('auth.login'))

            user = User(data)
            login_user(user, remember=True)
            log_audit(user.id, 'google_login', ip_address=request.remote_addr)
            flash(f'Welcome back, {user.full_name.split()[0]}! 👋', 'success')

        else:
            # New user — auto-register with Google
            import bcrypt, secrets as sec
            # Create a random unguessable password (they'll use Google to login)
            random_pw = sec.token_urlsafe(32)
            pw_hash   = User.hash_password(random_pw)
            # Dummy security answer
            ans_hash  = User.hash_password('google_oauth_user')

            user_id = query_db(
                """INSERT INTO users
                   (full_name, email, phone, password_hash, role,
                    security_question, security_answer_hash, is_active)
                   VALUES (%s, %s, '0000000000', %s, 'user',
                           'How did you register?', %s, TRUE)""",
                (google_name, google_email, pw_hash, ans_hash),
                commit=True
            )
            log_audit(user_id, 'google_register', 'users', user_id,
                      ip_address=request.remote_addr)

            data = query_db('SELECT * FROM users WHERE id=%s', (user_id,), one=True)
            user = User(data)
            login_user(user, remember=True)
            flash(f'Account created via Google! Welcome, {google_name.split()[0]} 🎉', 'success')

        # Redirect to appropriate dashboard
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.index'))

    except Exception as e:
        log.error(f'Google OAuth callback failed: {e}')
        flash('Google login failed. Please try again or use email/password.', 'error')
        return redirect(url_for('auth.login'))
