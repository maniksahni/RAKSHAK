from flask import Blueprint

valkyrie_bp = Blueprint('valkyrie', __name__)

from modules.valkyrie import routes
