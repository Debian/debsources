# Copyright (C) 2013  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

from __future__ import absolute_import

import logging
from logging import Formatter, FileHandler, StreamHandler

from flask import Flask

from debsources import mainlib
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
            self.app.config.update(config)

    def go(self):
        """
        Sets up SQLAlchemy, logging, and imports all the views.
        After creating an AppWrapper and calling this method, the app is ready.
        """
        if self.session is None:
            self.setup_sqlalchemy()

        self.setup_logging()

        # setup blueprint
        self.setup_blueprints()

    def setup_blueprints(self):
        if 'NAME' in self.app.config.keys():
            self.app.import_name = self.app.config.get('NAME')
        else:
            # don't fail with existing conf
            self.app.import_name = 'sources'
        if self.app.config.get('BLUEPRINT_COPYRIGHT'):
            from debsources.app.copyright import bp_copyright
            # add a url-prefix
            self.app.register_blueprint(bp_copyright,
                                        url_prefix='/copyright')
        if self.app.config.get('BLUEPRINT_PATCHES'):
            from debsources.app.patches import bp_patches
            # add a url-prefix
            self.app.register_blueprint(bp_patches,
                                        url_prefix='/patches')

        if self.app.config.get('BLUEPRINT_SOURCES'):
            from debsources.app.sources import bp_sources
            # add a url-prefix
            self.app.register_blueprint(bp_sources,
                                        # hook on the root
                                        url_prefix=None)

    def setup_conf(self):
        """
        Sets up the configuration, getting it from mainlib.
        """
        conf = mainlib.load_conf(mainlib.guess_conffile(), section="webapp")
        self.app.config.update(conf)

    def setup_sqlalchemy(self):
        """
        Creates an engine and a session for SQLAlchemy, using the database URI
        in the configuration.
        """
        db_uri = self.app.config["SQLALCHEMY_DATABASE_URI"]
        e, s = _get_engine_session(db_uri,
                                   verbose=self.app.config["SQLALCHEMY_ECHO"])
        self.engine, self.session = e, s

    def setup_logging(self):
        """
        Sets up everything needed for logging.
        """
        fmt = Formatter('%(asctime)s %(levelname)s: %(message)s '
                        + '[in %(pathname)s:%(lineno)d]')
        log_level = logging.INFO
        try:
            log_level = mainlib.LOG_LEVELS[self.app.config["LOG_LEVEL"]]
        except KeyError:  # might be raised by both "config" and "LOG_LEVELS",
            pass          # same treatment: fallback to default log_level

        stream_handler = StreamHandler()
        stream_handler.setFormatter(fmt)
        stream_handler.setLevel(log_level)
        self.app.logger.addHandler(stream_handler)

        if "LOG_FILE" in self.app.config:
            file_handler = FileHandler(self.app.config["LOG_FILE"])
            file_handler.setFormatter(fmt)
            file_handler.setLevel(log_level)
            self.app.logger.addHandler(file_handler)
