import os

_basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# grand-parent folder

DEBUG = True

SECRET_KEY = 'SecretKeyForSessionSigning'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(_basedir, 'app.db')
#SQLALCHEMY_MIGRATE_REPO = os.path.join(_basedir, 'db_repository')
#DATABASE_CONNECT_OPTIONS = {}

#THREADS_PER_PAGE = 8

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"

SQLALCHEMY_ECHO = True

APP_FOLDER = "app"

SOURCES_FOLDER = APP_FOLDER + "/static/data" # for listing folders and files
SOURCES_STATIC = "/static/data" # for external links
