from flask import Blueprint

xray_vision_bp = Blueprint('xray_vision', __name__)

from modules.xray_vision import routes
