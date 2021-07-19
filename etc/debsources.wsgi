# WSGI Python file to bridge apache2 / Flask application

import sys
from pathlib import Path

DEBSOURCES_LIB = Path(__file__).resolve().parent.parent / "lib"
sys.path.append(str(DEBSOURCES_LIB))

from debsources.app import app_wrapper

app_wrapper.go()
application = app_wrapper.app
