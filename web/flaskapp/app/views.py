from flask import render_template, redirect, url_for

from app import app
from models_app import Package_app, Version_app
from forms import SearchForm

def get_letters():
    return ['0','1','2','3','4','5','6','7','8','9',
            'a','b','c','d','e','f','g','h','i','j','k',
            'liba','libb','libc','libd','libe','libf','libg',
            'libh','libi','libj','libk','libl','libm','libn',
            'libo','libp','libq','libr','libs','libt','libu',
            'libv','libw','libx','liby','libz',
            'm','n','o','p','q','r','s','t','u','v','w','x','y','z']

@app.route('/', methods=['POST', 'GET']) # navigation
@app.route('/nav/', methods=['POST', 'GET'])
def index():
    #packages = Package_app.query.order_by(Package_app.name).paginate(1, 10).items
    searchform = SearchForm()
    if searchform.validate_on_submit():
        return redirect(url_for("search", packagename=searchform.packagename.data))
    return render_template('index.html',
                           searchform=searchform,
                           letters=get_letters())

#@app.route('/nav/search/', methods=['POST'])
@app.route('/nav/search/<packagename>/')
def search(packagename):
    packagename = packagename.replace('%', '').replace('_', '')
    exact_matching = Package_app.query.filter_by(name=packagename).first()
    other_results = Package_app.query.filter(Package_app.name.contains(packagename))
    return render_template('search.html',
                           exact_matching=exact_matching,
                           other_results=other_results)

@app.route('/nav/list/')
@app.route('/nav/list/<int:page>/')
def list(page=1):
    packages = Package_app.query.order_by(Package_app.name).paginate(page, 20, False)
    return render_template('list.html',
                           packages=packages)

@app.route('/nav/letter/')
@app.route('/nav/letter/<letter>')
def letter(letter='a'):
    if letter in get_letters():
        packages = Package_app.query.filter(Package_app.name.startswith(letter))
        return render_template("letter.html",
                               packages=packages)
    else:
        return render_template('404.html'), 404


@app.route('/nav/package/<packagename>/<packageversion>/')
def package(packagename, packageversion):
    pass
