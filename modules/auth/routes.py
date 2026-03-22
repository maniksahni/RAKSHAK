from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from flask_login import logout_user, login_required, current_user
from models import query_db, log_audit
from app import limiter
import re

auth_bp = Blueprint('auth', __name__)


def validate_phone(p):
    return re.match(r'^\d{10}$', p.strip())


# ── Register (Google-only — page renders OAuth prompt) ────────────────────────
@auth_bp.route('/register')
@limiter.limit('10 per hour')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html')


# ── Login (Google-only — page renders OAuth prompt) ───────────────────────────
@auth_bp.route('/login')
@limiter.limit('20 per hour')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('auth/login.html')


# ── Logout ────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    log_audit(current_user.id, 'logout', ip_address=request.remote_addr)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ── Profile ───────────────────────────────────────────────────────────────────
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name', '').strip()
            phone     = request.form.get('phone', '').strip()
            address   = request.form.get('address', '').strip()

            errors = []
            if not full_name or len(full_name) < 2:
                errors.append('Full name must be at least 2 characters.')
            if not validate_phone(phone):
                errors.append('Phone must be 10 digits.')
            if errors:
                return jsonify(success=False, errors=errors), 400

            query_db(
                'UPDATE users SET full_name=%s, phone=%s, address=%s WHERE id=%s',
                (full_name, phone, address, current_user.id), commit=True
            )

            log_audit(current_user.id, 'profile_update', 'users', current_user.id,
                      ip_address=request.remote_addr)
            return jsonify(success=True, message='Profile updated successfully!')

        except Exception as e:
            return jsonify(success=False, errors=[str(e)]), 500

    # Fetch trusted contacts
    contacts = query_db('SELECT * FROM trusted_contacts WHERE user_id=%s', (current_user.id,))
    return render_template('auth/profile.html', contacts=contacts)


# ── Trusted Contacts ──────────────────────────────────────────────────────────
@auth_bp.route('/contacts/add', methods=['POST'])
@login_required
def add_contact():
    try:
        count = query_db(
            'SELECT COUNT(*) as cnt FROM trusted_contacts WHERE user_id=%s',
            (current_user.id,), one=True
        )
        if count and count['cnt'] >= 5:
            return jsonify(success=False, error='Maximum 5 trusted contacts allowed.'), 400

        name         = request.form.get('contact_name', '').strip()
        email        = request.form.get('contact_email', '').strip().lower()
        phone        = request.form.get('contact_phone', '').strip()
        relationship = request.form.get('relationship', 'Friend').strip()

        if not all([name, email, phone]):
            return jsonify(success=False, error='All fields are required.'), 400

        cid = query_db(
            """INSERT INTO trusted_contacts (user_id, contact_name, contact_email, contact_phone, relationship)
               VALUES (%s, %s, %s, %s, %s)""",
            (current_user.id, name, email, phone, relationship), commit=True
        )
        log_audit(current_user.id, 'add_contact', 'trusted_contacts', cid,
                  ip_address=request.remote_addr)
        return jsonify(success=True, message='Contact added.', id=cid)

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@auth_bp.route('/contacts/<int:cid>/delete', methods=['DELETE'])
@login_required
def delete_contact(cid):
    try:
        query_db(
            'DELETE FROM trusted_contacts WHERE id=%s AND user_id=%s',
            (cid, current_user.id), commit=True
        )
        return jsonify(success=True, message='Contact removed.')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# ── Forgot Password (disabled — Google-only auth) ────────────────────────────
@auth_bp.route('/forgot-password')
def forgot_password():
    flash('RAKSHAK uses Google Sign-In only. No password to reset!', 'info')
    return redirect(url_for('auth.login'))
