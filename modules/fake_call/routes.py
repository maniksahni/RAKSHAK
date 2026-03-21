import logging
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required

log = logging.getLogger('rakshak')

fake_call_bp = Blueprint('fake_call', __name__)


@fake_call_bp.route('/')
@login_required
def index():
    return render_template('dashboard/fake_call.html')


@fake_call_bp.route('/schedule', methods=['POST'])
@login_required
def schedule_call():
    """Schedule a fake call after N seconds. The actual call is triggered
    client-side via JavaScript timers — this endpoint just acknowledges
    the request so the CSRF flow is satisfied."""
    try:
        data = request.get_json() or {}
        delay = data.get('delay', 30)
        caller = data.get('caller', 'Mom')

        try:
            delay = max(1, min(int(delay), 600))
        except (TypeError, ValueError):
            delay = 30

        return jsonify(success=True, delay=delay, caller=caller,
                       message=f'Fake call from {caller} scheduled in {delay}s.')

    except Exception as e:
        log.error(f'Fake call schedule failed: {e}')
        return jsonify(success=False, error='Failed to schedule call.'), 500
