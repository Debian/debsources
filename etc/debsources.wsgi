# # if the debsources Python module is not installed system-wide, you will need
# # to add its root directory to Python's path, e.g.:
#
# import sys, os
# DEBSOURCES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(DEBSOURCES_ROOT)

from debsources.app import app_wrapper
app_wrapper.go()
application = app_wrapper.app
