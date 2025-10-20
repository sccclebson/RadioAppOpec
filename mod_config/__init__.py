from flask import Blueprint
bp_config = Blueprint('bp_config', __name__, url_prefix='/config', template_folder='templates', static_folder='static')
from . import routes  # noqa: E402,F401