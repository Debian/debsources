import sys, os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_DIR, "web")

sys.path.append(WEB_DIR)

from app import app_wrapper
app_wrapper.go()
application = app_wrapper.app
