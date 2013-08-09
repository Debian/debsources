###################################
# Debsources webapp configuration #
###################################

# this file is loaded as a Python module from flask/app/__init__.py using a
# relative path ('../../../etc/appconfig.py')

import os, re


# the domain of the webapp, used in documentation:
DOMAIN = "sources.debian.net"
GITWEB_URL = "http://anonscm.debian.org/gitweb/?p=qa/debsources.git"

# the secret key for session signing:
# SECRET_KEY = 'some_hash' # not in use

# CSRF token for WTForms:
# we don't have any form which writes data
CSRF_ENABLED = False

# related session key:
# CSRF_SESSION_KEY = "some_hash" # not in use

# the place where the browser can GET the highlight.js library (JS + CSS):
HIGHLIGHT_JS_FOLDER = "/javascript/highlight"

# CSS style for highlight.js
# see http://softwaremaniacs.org/media/soft/highlight/test.html
# HIGHLIGHT_STYLE = "default"
HIGHLIGHT_STYLE = "googlecode"

# the place where the tango icons (or other icons) are :
ICONS_FOLDER = "/icons/Tango/"

# the Package Tracking System prefix to generate external URLs:
# (the package name will be concatenated)
PTS_PREFIX = "http://packages.qa.debian.org/"

# the root folder of the application, normally the "debsources" location:
ROOT_FOLDER = "/srv/debsources/"

# /!\ never set this to True in production:
DEBUG = False

# echoes or not the SQL requests to stdout (can be logged with Apache):
SQLALCHEMY_ECHO = False

# the uri of the database
SQLALCHEMY_DATABASE_URI = "sqlite:///" + \
    os.path.join(ROOT_FOLDER, "cache/sources.sqlite")

# where the sources are on the disk, for listing folders and files:
SOURCES_FOLDER = os.path.join(ROOT_FOLDER, "sources")

# where the sources are accessible for a browser, for raw links:
SOURCES_STATIC = "/data"

# where the models.py file is stored:
MODELS_FOLDER = os.path.join(ROOT_FOLDER, "web")

# where the last-update is stored, to be displayed in the footer
LAST_UPDATE_FILE = os.path.join(ROOT_FOLDER, "cache/last-update")

# where package prefixes to be used for navigation can be found
PKG_PREFIXES_FILE = os.path.join(ROOT_FOLDER, "cache/pkg-prefixes")
