#!/usr/bin/env python

# Debsources FastCGI entry point
# for Apache, just use:
# ScriptAlias / /path/to/debsources.fcgi
# in your conf

from flup.server.fcgi import WSGIServer

import sys, os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_DIR)

from app import app

if __name__ == '__main__':
    WSGIServer(app).run()