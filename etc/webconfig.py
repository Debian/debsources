# this file is loaded as a Python module from flask/app/__init__.py using a
# relative path ('../../../etc/appconfig.py')

DOMAIN = "sources.upsilon.cc"

#SECRET_KEY = 'SecretKeyForSessionSigning' # not in use

# we don't have any form which writes data
CSRF_ENABLED = False
#CSRF_SESSION_KEY = "somethingimpossibletoguess" # not in use

# the place where the browser can GET the highlight.js library (JS + CSS)
HIGHLIGHT_JS_FOLDER = "/javascript/highlight"

# the place where the icons are 

### PROD ###

DEBUG = False
SQLALCHEMY_ECHO = False
SQLALCHEMY_DATABASE_URI = 'sqlite:////srv/debsources/cache/sources.sqlite'
SOURCES_FOLDER = "/srv/debsources/sources/" # for listing folders and files
SOURCES_STATIC = "/data" # for external raw links
MODELS_FOLDER = "/srv/debsources/web"



### DEV ###

# DEBUG = True
# SQLALCHEMY_ECHO = True
# SQLALCHEMY_DATABASE_URI = 'sqlite:////var/www/debsources/app.db'
# SOURCES_FOLDER = "/var/www/debsources/app/static/data/" # for listing folders and files
# SOURCES_STATIC = "/data" # for external raw links
# MODELS_FOLDER = "/var/www/debsources/"
