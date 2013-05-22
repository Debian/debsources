from flask import render_template, redirect, url_for

from app import app
from models_app import Package_app, Version_app
from forms import SearchForm

@app.route('/', methods=['POST', 'GET']) # navigation
@app.route('/nav/', methods=['POST', 'GET'])
def index():
    #packages = Package_app.query.order_by(Package_app.name).paginate(1, 10).items
    searchform = SearchForm()
    if searchform.validate_on_submit():
        return redirect(url_for("search", packagename=searchform.packagename.data))
    return render_template('index.html',
                           searchform=searchform)

#@app.route('/nav/search/', methods=['POST'])
@app.route('/nav/search/<packagename>')
def search(packagename):
    exact_matching = Package_app.query.filter_by(name=packagename).first()
    other_results = Package_app.query.filter(Package_app.name.like('%'+packagename+'%'))
    return render_template('search.html',
                           exact_matching=exact_matching,
                           other_results=other_results)
