#!/usr/bin/python

if __name__ == "__main__":
    import sys
    import os

    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(PROJECT_DIR)

    from app import app_wrapper
    app_wrapper.go()
    app_wrapper.app.run(debug=True)
