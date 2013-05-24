from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)

import os, sys

grandparentdir = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, grandparentdir)

from app import views
