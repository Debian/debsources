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


SECRET_KEY = 'SecretKeyForSessionSigning'

#THREADS_PER_PAGE = 8

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"


# you have to set up flask/app/__init__.py:
# app.config.from_pyfile('path/to/this_file')

### PROD ###

DEBUG = False
SQLALCHEMY_ECHO = False
SQLALCHEMY_DATABASE_URI = 'sqlite:////srv/debsources/cache/app.db'
SOURCES_FOLDER = "/srv/debsources/sources/" # for listing folders and files
SOURCES_STATIC = "/data" # for external raw links
MODELS_FOLDER = "/srv/debsources/path/to/web"



### DEV ###

# DEBUG = True
# SQLALCHEMY_ECHO = True
# SQLALCHEMY_DATABASE_URI = 'sqlite:////var/www/debsources/app.db'
# SOURCES_FOLDER = "/var/www/debsources/app/static/data/" # for listing folders and files
# SOURCES_STATIC = "/data" # for external raw links
# MODELS_FOLDER = "/var/www/debsources/"
