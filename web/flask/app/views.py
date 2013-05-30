# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from flask import render_template, redirect, url_for, request, safe_join, \
    jsonify
from flask.views import View

from app import app
from models_app import Package_app, Version_app, Location, Directory, \
    SourceFile, PackageFolder, InvalidPackageOrVersionError
from forms import SearchForm

#import modules.tasks as tasks

@app.context_processor # variables needed by "base.html" skeleton
def skeleton_variables():
    return dict(packages_prefixes = Package_app.get_packages_prefixes(),
                searchform = SearchForm())

def deal_404_error(error, mode='html'):
    if mode == 'json':
        return jsonify(dict(error=404))
    else:
        return render_template('404.html'), 404

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

def deal_500_error(error, mode='html'):
    """ logs a 500 error and returns the correct template """
    app.logger.error(error)
    if mode == 'json':
        return jsonify(dict(error=500))
    else:
        return render_template('500.html'), 500

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

@app.route('/doc/url/')
def doc_url():
    return render_template('doc_url.html')

@app.route('/doc/api/')
def doc_api():
    return render_template('doc_api.html')


@app.route('/')
@app.route('/nav/') # navigation
def index():
    return render_template('index.html')


### SEARCH ###

@app.route('/search/', methods=['GET', 'POST'])
def receive_search():
    searchform = SearchForm(request.form)
    if searchform.validate_on_submit():
        return redirect(url_for("search_html",
                                query=searchform.query.data))
    else:
        # we return the form, to display the errors
        return render_template('index.html', searchform=searchform)

@app.route('/mr/search/')
def receive_empty_search_json():
    return deal_404_error(None, 'json')

class SearchView(View):
    def __init__(self, mode='html'):
        self.mode = mode
    
    def dispatch_request(self, query=None):
        self.query = query.replace('%', '').replace('_', '')
        context = self.get_objects()
        if self.mode == 'html':
            return render_template("search.html", **context)
        elif self.mode == 'json':
            return jsonify(**context)
    
    def get_objects(self):
        try:
            exact_matching = Package_app.query.filter_by(
                name=self.query).first().to_dict()
        
            other_results = Package_app.query.filter(
                Package_app.name.contains(
                    self.query)).order_by(Package_app.name)
        except Exception as e:
            return deal_500_error(e, mode=self.mode)
        
        other_results = [o.to_dict() for o in other_results]
        results = dict(exact_matching=exact_matching,
                       other_results=other_results)
        return dict(results=results, query=self.query)


app.add_url_rule('/search/<query>/',
                 view_func=SearchView.as_view('search_html', mode='html'))

app.add_url_rule('/mr/search/<query>/',
                 view_func=SearchView.as_view('search_json', mode='json'))

### NAVIGATION ###

@app.route('/nav/list/')
@app.route('/nav/list/<int:page>/')
def list(page=1):
    try:
        packages = Package_app.query.order_by(
            Package_app.name).paginate(page, 20, False)
    except Exception as e:
        return deal_500_error(e)
    return render_template('list.html',
                           packages=packages,
                           page=page)

@app.route('/nav/letter/')
@app.route('/nav/letter/<letter>')
def letter(letter='a'):
    if letter in Package_app.get_packages_prefixes():
        try:
            packages = Package_app.query.filter(
                Package_app.name.startswith(letter)).order_by(Package_app.name)
        except Exception as e:
            return deal_500_error(e)
        return render_template("letter.html",
                               packages=packages,
                               letter=letter)
    else:
        return render_template('404.html'), 404


@app.route('/src/<package>/')
@app.route('/src/<package>/<version>/')
@app.route('/src/<package>/<version>/<path:path_to>', methods=['POST', 'GET'])
def source(package, version=None, path_to=None):
    try:
        location = Location(package, version, path_to)
    except InvalidPackageOrVersionError: # 404
        return render_template("404.html"), 404
    
    if location.ispackage(): # it's a package, we list its versions
        location = PackageFolder(package)
        
        return render_template("source_package.html",
                               package=location.get_package_name(),
                               versions=location.get_versions(),
                               pathl=location.get_path_links())
    
    if location.isdir(): # it's a folder, we list its content
        location = Directory(package, version, path_to)
        
        return render_template("source_folder.html",
                               files=location.get_subfiles(),
                               dirs=location.get_subdirs(),
                               pathl=location.get_path_links(),
                               parentfolder=not(location.is_top_folder()))
                                 # we want '..', except for a package file
    
    elif location.isfile(): # it's a file, we check if it's a text file
        location = SourceFile(package, version, path_to)
        
        if not(location.istextfile()): # binary file
            return redirect(location.get_raw_url())
        # else: text file, we display the source code
        try:
            highlight = request.args.get('hl')
        except (KeyError, ValueError, TypeError):
            hl = None
        try:
            msg = request.args.get('msg')
        except (KeyError, ValueError, TypeError):
            msg = None
            
        location.prepare_code(highlight=highlight, msg=msg)
        
        return render_template("source_file.html",
                               code = location.get_code(),
                               nlines=location.get_number_of_lines(),
                               msg=location.get_msgdict(),
                               pathl=location.get_path_links(),
                               raw_url=location.get_raw_url(),
                               file_language=location.get_file_language())
    
    else: # 404
        return render_template('404.html'), 404
