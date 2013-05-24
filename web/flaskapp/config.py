import os

_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

SECRET_KEY = 'SecretKeyForSessionSigning'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_basedir, 'app.db')
#SQLALCHEMY_MIGRATE_REPO = os.path.join(_basedir, 'db_repository')
#DATABASE_CONNECT_OPTIONS = {}

#THREADS_PER_PAGE = 8

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"

SQLALCHEMY_ECHO = True

SOURCES_FOLDER = "app/static/data" # for listing files
SOURCES_SERVER = "/static/data" # for get request from the browser
# to test this: $ chromium-browser --disable-web-security
