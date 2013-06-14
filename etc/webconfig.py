###################################
# Debsources webapp configuration #
###################################

# this file is loaded as a Python module from flask/app/__init__.py using a
# relative path ('../../../etc/appconfig.py')

import os, re


# the domain of the webapp, used in documentation:
DOMAIN = "sources.debian.net"
GITWEB_URL = "http://git.upsilon.cc/?p=debsources.git"

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

# patterns for language detection
# each language is associated with a list of regex, matching the filename
HIGHLIGHT_CLASSES = [
    ("haskell", [r'.hs$', r'.lhs$']),
    ("python", [r'.py$']),
    ("ruby", [r'.rb$']),
    ("perl", [r'.pl$']),
    ("php", [r'.php$']),
    ("scala", [r'.scala$']),
    ("go", [r'.go$']),
    ("xml", [r'.xml$']),
    # we let hl.js distinguish django and html (both .html)
    ("markdown", [r'.md$']),
    ("css", [r'.css$']),
    ("json", [r'.json$']),
    ("javascript", [r'.js$']),
    ("coffeescript", [r'.coffee$']),
    ("lua", [r'.lua$']),
    ("java", [r'.java$']),
    ("cpp", [r'.h$', r'.c$', r'.cpp$', r'.hpp$', r'.C$', r'.cc$']),
    ("diff", [r'.patch$', r'.diff$']),
    ("bash", [r'.sh$']),
    ("tex", [r'.tex$']),
    ("no-highlight", [r'.txt$', r'^README$', r'^TODO$', r'^BUGS$',
                      r'Makefile', r'makefile']),
    ]

# strings which will be searched in the mime type of a file to determine
# if the file should be displayed or downloaded as a raw file:
TEXT_FILE_MIMES = [
    "text",
    "xml",
    ]
    

# the place where the tango icons (or other icons) are :
ICONS_FOLDER = "/icons/Tango/"

# the Package Tracking System prefix to generate external URLs:
# (the package name will be concatenated)
PTS_PREFIX = "http://packages.qa.debian.org/"

### PROD ###

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

# where the last-update is stored, to be displayed in the footer:
LAST_UPDATE_FILE = os.path.join(ROOT_FOLDER, "cache/last-update")


### DEV ###

# DEBUG = True
# SQLALCHEMY_ECHO = True
