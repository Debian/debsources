import sys, os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_DIR, "web/flask")

sys.path.append(WEB_DIR)

from app import app as application