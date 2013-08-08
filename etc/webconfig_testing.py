import os

ROOT_FOLDER = "/home/matthieu/work/debian/debsources/"
SOURCES_STATIC = "/static/data"
MODELS_FOLDER = os.path.join(ROOT_FOLDER, "web")
LAST_UPDATE_FILE = os.path.join(ROOT_FOLDER, "cache/last-update")
TESTING = True
SOURCES_FOLDER = "/home/matthieu/work/debian/debsources/web/flask/tests/sources"
SQLALCHEMY_DATABASE_URI = "postgresql://matthieu:matthieu@localhost:5432/debsources_test"
