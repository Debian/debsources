from flask import render_template

from app import app, db
from models import Package, Version

from flask.ext.sqlalchemy import BaseQuery

@app.route('/') # navigation
def index():
    #a=BaseQuery(Package, session=db.session).paginate(1).items
    #packages = db.session.query(Package).paginate(1, 10, False).items#all()
    packages = db.session.query(Package).order_by(Package.name).limit(50)
    return render_template('index.html',
                           packages=packages)#packages[:])
