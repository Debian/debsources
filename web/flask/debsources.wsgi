import sys, os


config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                                           os.path.abspath(__file__)))),
                           "etc/webconfig_local.py")
os.environ["DEBSOURCES_CONFIG"] = config_file

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_DIR)

from app import app as application