from flask import render_template

from app import app, db
from models import Package, Version

@app.route('/') # navigation
def index():
    packages = db.session.query(Package).all()
    return render_template('index.html',
                           packages=packages[:50])
