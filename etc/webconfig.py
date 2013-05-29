# this file is loaded as a Python module from flask/app/__init__.py using a
# relative path ('../../../etc/appconfig.py')

SECRET_KEY = 'SecretKeyForSessionSigning'

#THREADS_PER_PAGE = 8

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"


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
