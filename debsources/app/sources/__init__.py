from flask import Blueprint

# naming rule: bp_{dirname}
bp_sources = Blueprint('sources',
                       __name__,
                       template_folder='templates',
                       static_url_path='/static/sources',
                       static_folder='static')

from . import routes  # NOQA
