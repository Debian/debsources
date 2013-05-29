import sys

PROJECT_DIR = '/srv/www/debsources/web/flask'
sys.path.append(PROJECT_DIR)

from app import app as application