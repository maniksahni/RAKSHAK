from flask import render_template
from flask_login import login_required
from modules.xray_vision import xray_vision_bp


@xray_vision_bp.route('/')
@login_required
def index():
    return render_template('xray_vision/index.html')
