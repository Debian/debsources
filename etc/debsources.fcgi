#!/usr/bin/env python

# Debsources FastCGI entry point
# for Apache, just use:
# ScriptAlias / /path/to/debsources.fcgi/
# in your conf

from flup.server.fcgi import WSGIServer

# # if the debsources Python module is not installed system-wide, you will need
# # to add its root directory to Python's path, e.g.:
#
# import sys, os
# DEBSOURCES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(DEBSOURCES_ROOT)

from debsources.app import app_wrapper


if __name__ == '__main__':
    app_wrapper.go()
    WSGIServer(app_wrapper.app).run()
