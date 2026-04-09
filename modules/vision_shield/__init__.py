from flask import Blueprint

vision_shield_bp = Blueprint('vision_shield', __name__)

from modules.vision_shield import routes
