# # if the debsources Python module is not installed system-wide, you will need
# # to add its root directory to Python's path, e.g.:
#
import os
import sys
DEBSOURCES_LIB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'lib')
sys.path.append(DEBSOURCES_LIB)

from debsources.app import app_wrapper
app_wrapper.go()
application = app_wrapper.app
