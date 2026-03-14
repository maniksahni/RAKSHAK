from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, session)
from flask_login import login_user, logout_user, login_required, current_user
from models import User, query_db, log_audit
from app import limiter
import bcrypt
import re

auth_bp = Blueprint('auth', __name__)


def validate_password(p):
    return (len(p) >= 8 and
            re.search(r'[A-Z]', p) and
            re.search(r'[a-z]', p) and
            re.search(r'\d', p) and
            re.search(r'[!@#$%^&*]', p))


def validate_phone(p):
    return re.match(r'^\d{10}$', p.strip())


# ── Register ──────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        try:
            full_name          = request.form.get('full_name', '').strip()
            email              = request.form.get('email', '').strip().lower()
            phone              = request.form.get('phone', '').strip()
            password           = request.form.get('password', '')
            confirm_password   = request.form.get('confirm_password', '')
            security_question  = request.form.get('security_question', '').strip()
            security_answer    = request.form.get('security_answer', '').strip().lower()

            # Validations
            errors = []
            if not full_name or len(full_name) < 2:
                errors.append('Full name must be at least 2 characters.')
            if not re.match(r'^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$', email):
                errors.append('Invalid email address.')
            if not validate_phone(phone):
                errors.append('Phone must be 10 digits.')
            if password != confirm_password:
                errors.append('Passwords do not match.')
            if not validate_password(password):
                errors.append('Password must be 8+ chars with uppercase, lowercase, digit, special char.')
            if not security_question or not security_answer:
                errors.append('Security question and answer are required.')

            if errors:
                return jsonify(success=False, errors=errors), 400

            # Check duplicate email
            existing = query_db('SELECT id FROM users WHERE email=%s', (email,), one=True)
            if existing:
                return jsonify(success=False, errors=['Email already registered.']), 409

            pw_hash  = User.hash_password(password)
            ans_hash = User.hash_password(security_answer)

            user_id = query_db(
                """INSERT INTO users (full_name, email, phone, password_hash, role,
                   security_question, security_answer_hash)
                   VALUES (%s, %s, %s, %s, 'user', %s, %s)""",
                (full_name, email, phone, pw_hash, security_question, ans_hash),
                commit=True
            )
            log_audit(user_id, 'register', 'users', user_id, ip_address=request.remote_addr)
            flash('Account created successfully! Please log in.', 'success')
            return jsonify(success=True, redirect=url_for('auth.login'))

        except Exception as e:
            return jsonify(success=False, errors=[f'Registration failed: {str(e)}']), 500

    return render_template('auth/register.html')


# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per hour')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        try:
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            if not email or not password:
                return jsonify(success=False, errors=['Email and password are required.']), 400

            data = query_db('SELECT * FROM users WHERE email=%s', (email,), one=True)
            if not data or not User.check_password(password, data['password_hash']):
                return jsonify(success=False, errors=['Invalid email or password.']), 401

            if not data['is_active']:
                return jsonify(success=False, errors=['Your account has been deactivated.']), 403

            user = User(data)
            login_user(user, remember=True)
            log_audit(user.id, 'login', ip_address=request.remote_addr)

            next_url = request.args.get('next')
            if user.is_admin:
                dest = next_url or url_for('admin.dashboard')
            else:
                dest = next_url or url_for('dashboard.index')

            return jsonify(success=True, redirect=dest)

        except Exception as e:
            return jsonify(success=False, errors=[f'Login error: {str(e)}']), 500

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

            # Password change (optional)
            new_password = request.form.get('new_password', '')
            if new_password:
                curr_password = request.form.get('current_password', '')
                data = query_db('SELECT password_hash FROM users WHERE id=%s',
                                (current_user.id,), one=True)
                if not User.check_password(curr_password, data['password_hash']):
                    return jsonify(success=False, errors=['Current password is incorrect.']), 400
                if not validate_password(new_password):
                    return jsonify(success=False, errors=['New password does not meet requirements.']), 400
                pw_hash = User.hash_password(new_password)
                query_db('UPDATE users SET password_hash=%s WHERE id=%s',
                         (pw_hash, current_user.id), commit=True)

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


# ── Forgot Password ───────────────────────────────────────────────────────────
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def forgot_password():
    if request.method == 'POST':
        step = request.form.get('step', '1')
        try:
            if step == '1':
                email = request.form.get('email', '').strip().lower()
                data  = query_db('SELECT id, security_question FROM users WHERE email=%s',
                                 (email,), one=True)
                if not data:
                    return jsonify(success=False, error='Email not found.'), 404
                session['reset_email'] = email
                return jsonify(success=True,
                               question=data['security_question'],
                               user_id=data['id'])

            elif step == '2':
                email  = session.get('reset_email')
                answer = request.form.get('security_answer', '').strip().lower()
                if not email:
                    return jsonify(success=False, error='Session expired.'), 400
                data = query_db('SELECT security_answer_hash FROM users WHERE email=%s',
                                (email,), one=True)
                if not data or not User.check_password(answer, data['security_answer_hash']):
                    return jsonify(success=False, error='Incorrect answer.'), 401
                session['reset_verified'] = True
                return jsonify(success=True, message='Verified!')

            elif step == '3':
                email = session.get('reset_email')
                if not session.get('reset_verified') or not email:
                    return jsonify(success=False, error='Session expired.'), 400
                new_password = request.form.get('new_password', '')
                if not validate_password(new_password):
                    return jsonify(success=False,
                                   error='Password must be 8+ chars with uppercase, lowercase, digit, special char.'), 400
                pw_hash = User.hash_password(new_password)
                query_db('UPDATE users SET password_hash=%s WHERE email=%s',
                         (pw_hash, email), commit=True)
                session.pop('reset_email', None)
                session.pop('reset_verified', None)
                log_audit(None, 'password_reset', 'users', ip_address=request.remote_addr)
                return jsonify(success=True, redirect=url_for('auth.login'))

        except Exception as e:
            return jsonify(success=False, error=str(e)), 500

    return render_template('auth/forgot_password.html')
