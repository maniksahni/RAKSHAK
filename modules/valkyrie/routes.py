from flask import render_template
from flask_login import login_required, current_user
from modules.valkyrie import valkyrie_bp

@valkyrie_bp.route('/')
@login_required
def index():
    return render_template('valkyrie/index.html')
