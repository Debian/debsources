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
import sys
import logging
from logging import Formatter, StreamHandler
from ConfigParser import SafeConfigParser

from flask import Flask

from debsources.sqla_session import _get_engine_session

class AppWrapper(object):
    """
    Contains an app and a session, and provides ways to drive all the init
    steps separately.
    """
    def __init__(self, config=None, session=None):
        """
        Creates a Flask application and sets up its configuration.
        If config and/or session are provided, they will overload the
        default behavior.
        """
        self.session = session
        self.app = Flask(__name__)
        
        if config is None:
            self.setup_conf()
        else:
            self.app.config = config
    
    def go(self):
        """
        Sets up SQLAlchemy, logging, and imports all the views.
        After creating an AppWrapper and calling this method, the app is ready.
        """
        if self.session is None:
            self.setup_sqlalchemy()
        
        self.setup_logging()
        
        # importing the views creates all the routing for the app
        from debsources.app import views
        
    def setup_conf(self):
        """
        Sets up the configuration.
        Will first try in etc/config.local.ini, then in etc/config.ini.
        """
        parser = SafeConfigParser()
        conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '../../etc/config.local.ini')
        if not(os.path.exists(conf_file)):
            conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     '../../etc/config.ini')

        parser.read(conf_file)

        for (key, value) in parser.items("webapp"):
            if value.lower() == "false":
                value = False
            elif value.lower() == "true":
                value = True
            self.app.config[key.upper()] = value
        
        # needs to be done at this point, because we need the value in the conf
        sys.path.append(self.app.config['PYTHON_DIR'])
        
    def setup_sqlalchemy(self):
        """
        Creates an engine and a session for SQLAlchemy, using the database URI
        in the configuration.
        """
        db_uri = self.app.config["SQLALCHEMY_DATABASE_URI"]
        e, s = _get_engine_session(db_uri,
                                   verbose = self.app.config["SQLALCHEMY_ECHO"])
        self.engine, self.session = e, s

    def setup_logging(self):
        """
        Sets up everything needed for logging.
        """
        handler = StreamHandler()
        handler.setFormatter(Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
                ))
        handler.setLevel(logging.INFO)
        self.app.logger.addHandler(handler)
