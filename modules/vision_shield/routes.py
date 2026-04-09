from flask import render_template
from flask_login import login_required
from modules.vision_shield import vision_shield_bp


@vision_shield_bp.route('/')
@login_required
def index():
    return render_template('vision_shield/index.html')
