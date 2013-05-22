from flask import render_template

from app import app
from models_app import Package_app, Version_app

@app.route('/') # navigation
def index():
    packages = Package_app.query.order_by(Package_app.name).paginate(1, 10).items
    return render_template('index.html',
                           packages=packages)
