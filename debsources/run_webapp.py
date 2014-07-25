#!/usr/bin/python

import sys
import os
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Flask app, for dev/debug.')
    parser.add_argument('--host', type=str, default='127.0.0.1', required=False,
                        help='Host, use 0.0.0.0 to listen on all IPs.')
    parser.add_argument('--port', type=int, default=5000, required=False,
                        help='Port in use')
    args = parser.parse_args()

    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(PROJECT_DIR)

    from debsources.app import app_wrapper
    app_wrapper.go()
    app_wrapper.app.run(debug=True, host=args.host, port=args.port)
