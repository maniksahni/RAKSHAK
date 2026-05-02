import os
import re

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from modules.valkyrie import valkyrie_bp
from app import limiter


def _effective_valkyrie_pin():
    configured = (os.environ.get('VALKYRIE_PIN') or '').strip()
    if re.fullmatch(r'\d{4}', configured or ''):
        return configured

    digits = ''.join(ch for ch in str(getattr(current_user, 'phone', '') or '') if ch.isdigit())
    if len(digits) >= 4:
        candidate = digits[-4:]
        if len(set(candidate)) > 1:
            return candidate
    return None

@valkyrie_bp.route('/')
@login_required
def index():
    return render_template('valkyrie/index.html')


@valkyrie_bp.route('/verify-pin', methods=['POST'])
@login_required
@limiter.limit('60 per hour;15 per minute')
def verify_pin():
    data = request.get_json(silent=True) or {}
    submitted = str(data.get('pin') or '').strip()
    if not re.fullmatch(r'\d{4}', submitted):
        return jsonify(success=False, error='Invalid PIN format.'), 400

    expected = _effective_valkyrie_pin()
    if not expected:
        return jsonify(success=False, error='Valkyrie PIN is not configured.'), 503

    return jsonify(success=(submitted == expected))
