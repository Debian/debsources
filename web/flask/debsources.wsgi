import sys

PROJECT_DIR = '/srv/debsources/web/flask/'
sys.path.append(PROJECT_DIR)

from app import app as application