# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
from logging import Formatter, StreamHandler
from ConfigParser import SafeConfigParser

from flask import Flask

app = Flask(__name__)

# Configuration
parser = SafeConfigParser()
conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          '../../../etc/config.local.ini')
if not(os.path.exists(conf_file)):
    conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '../../../etc/config.ini')

parser.read(conf_file)

for (key, value) in parser.items("webapp"):
    if value.lower() == "false":
        value = False
    elif value.lower() == "true":
        value = True
    app.config[key.upper()] = value

import sys
sys.path.append(app.config['PYTHON_DIR'])

from dbutils import _get_engine_session, _close_session

# SQLAlchemy
engine, session = _get_engine_session(app.config["SQLALCHEMY_DATABASE_URI"],
                                     verbose = app.config["SQLALCHEMY_ECHO"])

@app.teardown_appcontext
def shutdown_session(exception=None):
    _close_session(session)


from app import views

# logging
import sys
handler = StreamHandler()
handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
        ))
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
