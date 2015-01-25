# Copyright (C) 2013-2014  Matthieu Caneill <matthieu.caneill@gmail.com>
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import os

from debian.debian_support import version_compare
from flask import render_template, redirect, url_for, request, jsonify
from flask.views import View
from sqlalchemy import func as sql_func

from debsources import local_info

from debsources.sqla_session import _close_session


from debsources.app import app_wrapper
app = app_wrapper.app
session = app_wrapper.session

from debsources.excepts import (
    InvalidPackageOrVersionError, FileOrFolderNotFound,
    Http500Error, Http404Error, Http404ErrorSuggestions, Http403Error)
from debsources.models import (
    Ctag, Package, PackageName, Checksum, Location, Directory,
    SourceFile, File, Suite)
from debsources.app.sourcecode import SourceCodeIterator
from debsources.app.forms import SearchForm
from debsources.app.infobox import Infobox

from debsources.app.extract_stats import extract_stats
from debsources.consts import SLOCCOUNT_LANGUAGES, SUITES
from debsources import statistics

from debsources.app.pagination import Pagination


@app.teardown_appcontext
def shutdown_session(exception=None):
    _close_session(session)


# variables needed by "base.html" skeleton
# packages_prefixes and search form (for the left menu),
# last_update (for the footer)
@app.context_processor
def skeleton_variables():
    update_ts_file = os.path.join(app.config['CACHE_DIR'], 'last-update')
    last_update = local_info.read_update_ts(update_ts_file)

    packages_prefixes = PackageName.get_packages_prefixes(
        app.config["CACHE_DIR"])

    credits_file = os.path.join(app.config["LOCAL_DIR"], "credits.html")
    credits = local_info.read_html(credits_file)

    return dict(packages_prefixes=packages_prefixes,
                searchform=SearchForm(),
                last_update=last_update,
                credits=credits)


# jinja2 Filter to format big numbers
def format_big_num(num):
    try:
        res = "{:,}".format(num)
    except:
        res = num
    return res

app.jinja_env.filters['format_big_num'] = format_big_num

# PAGINATION #


def url_for_other_page(page):
    args = dict(request.args.copy())
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page


# GENERAL VIEW HANDLING #

# subclass this to add a view, linkable with add_url
# this allows one view to work with several templates (html, json, ...)
class GeneralView(View):
    def __init__(self, render_func=jsonify, err_func=lambda *x: x):
        """
        render_func: the render function, e.g. jsonify or render_template
        err_func: the function called when an error occurs
        """
        self.render_func = render_func
        self.err_func = err_func

    def dispatch_request(self, **kwargs):
        """
        renders the view, or call the error function with the error and
        the http error code (404 or 500)
        """
        try:
            context = self.get_objects(**kwargs)
            return self.render_func(**context)
        except Http500Error as e:
            return self.err_func(e, http=500)
        except Http404Error as e:
            return self.err_func(e, http=404)
        except Http403Error as e:
            return self.err_func(e, http=403)


# ERRORS #

def deal_error(error, http=404, mode='html'):
    """ spreads the error in the right place (404 or 500) """
    if http == 404:
        return deal_404_error(error, mode)
    elif http == 500:
        return deal_500_error(error, mode)
    elif http == 403:
        return deal_403_error(error, mode)
    else:
        raise Exception("Unimplemented HTTP error: %s" % str(http))


def deal_404_error(error, mode='html'):
    if mode == 'json':
        return jsonify(dict(error=404))
    else:
        if isinstance(error, Http404ErrorSuggestions):
            # let's suggest all the possible locations with a different
            # package version
            possible_versions = PackageName.list_versions(
                session, error.package)
            suggestions = ['/'.join(filter(None,
                                    [error.package, v.version, error.path]))
                           for v in possible_versions]
            return render_template('404_suggestions.html',
                                   suggestions=suggestions), 404
        else:
            return render_template('404.html'), 404


@app.errorhandler(404)
def page_not_found(e):
    return deal_404_error(e)


def deal_500_error(error, mode='html'):
    """ logs a 500 error and returns the correct template """
    app.logger.exception(error)

    if mode == 'json':
        return jsonify(dict(error=500))
    else:
        return render_template('500.html'), 500


@app.errorhandler(500)
def server_error(e):
    return deal_500_error(e)


def deal_403_error(error, mode='html'):
    if mode == 'json':
        return jsonify(dict(error=403))
    else:
        return render_template('403.html'), 403


@app.errorhandler(403)  # NOQA
def server_error(e):
    return deal_403_error(e)


# PING #

# this is used to check the health of the service
# for example by codesearch.debian.net
# If we want to stop traffic from codesearch.d.n, just return 500 error

@app.route('/api/ping/')
def ping():
    update_ts_file = os.path.join(app.config['CACHE_DIR'], 'last-update')
    last_update = local_info.read_update_ts(update_ts_file)
    try:
        session.query(Package).first().id  # database check
    except:
        return jsonify(dict(status="db error", http_status_code=500)), 500
    return jsonify(dict(status="ok",
                        http_status_code=200,
                        last_update=last_update))


# INDEX, DESCRIPTION, DOCUMENTATION, ABOUT #

@app.route('/')
def index():
    news_file = os.path.join(app.config["LOCAL_DIR"], "news.html")
    news = local_info.read_html(news_file)

    return render_template('index.html', news=news)


@app.route('/doc/')
def doc():
    return render_template('doc.html')


@app.route('/doc/url/')
def doc_url():
    return render_template('doc_url.html')


@app.route('/doc/api/')
def doc_api():
    return render_template('doc_api.html')


@app.route('/doc/overview/')
def doc_overview():
    return render_template('doc_overview.html')


@app.route('/about/')
def about():
    return render_template('about.html')


if 'SERVE_STATIC_FILES' in app.config and app.config['SERVE_STATIC_FILES']:
    import flask

    @app.route('/javascript/<path:path>')
    def javascript(path):
        return flask.send_from_directory('/usr/share/javascript/', path)

    @app.route('/icons/<path:path>')
    def icons(path):
        return flask.send_from_directory('/usr/share/icons/', path)


# SEARCH #

@app.route('/search/', methods=['GET', 'POST'])
def receive_search():
    searchform = SearchForm(request.form)
    if searchform.validate_on_submit():
        params = dict(query=searchform.query.data)
        suite = searchform.suite.data
        if suite:
            params["suite"] = suite
        return redirect(url_for("search_html", **params))
    else:
        # we return the form, to display the errors
        return render_template('index.html', searchform=searchform)

# @app.route('/api/search/')
# def receive_empty_search_json():
#     return deal_404_error(None, 'json')


class SearchView(GeneralView):
    def get_objects(self, query=None):
        """ processes the search query and renders the results in a dict """
        query = query.replace('%', '').replace('_', '')
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        # if suite is not specified
        if not suite:
            try:
                exact_matching = (session.query(PackageName)
                                  .filter_by(name=query)
                                  .first())

                other_results = (session.query(PackageName)
                                 .filter(sql_func.lower(PackageName.name)
                                         .contains(query.lower()))
                                 .order_by(PackageName.name)
                                 )
            except Exception as e:
                raise Http500Error(e)  # db problem, ...
        else:
            try:
                exact_matching = (session.query(PackageName)
                                  .filter(sql_func.lower(Suite.suite)
                                          == suite)
                                  .filter(Suite.package_id == Package.id)
                                  .filter(Package.name_id == PackageName.id)
                                  .filter(PackageName.name == query)
                                  .first())

                other_results = (session.query(PackageName)
                                 .filter(sql_func.lower(Suite.suite)
                                         == suite)
                                 .filter(Suite.package_id == Package.id)
                                 .filter(Package.name_id == PackageName.id)
                                 .filter(sql_func.lower(PackageName.name)
                                         .contains(query.lower()))
                                 .order_by(PackageName.name))
            except Exception as e:
                raise Http500Error(e)  # db problem, ...

        if exact_matching is not None:
            exact_matching = exact_matching.to_dict()
        if other_results is not None:
            other_results = [o.to_dict() for o in other_results]
            # we exclude the 'exact' matching from other_results:
            other_results = filter(lambda x: x != exact_matching,
                                   other_results)

        results = dict(exact=exact_matching,
                       other=other_results)
        return dict(results=results, query=query, suite=suite)

# SEARCH ROUTE (HTML)
app.add_url_rule('/search/<query>/', view_func=SearchView.as_view(
    'search_html',
    render_func=lambda **kwargs: render_template('search.html', **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))

# SEARCH ROUTE (JSON)
app.add_url_rule('/api/search/<query>/', view_func=SearchView.as_view(
    'search_json',
    render_func=jsonify,
    err_func=lambda e, **kwargs: deal_error(e, mode='json', **kwargs)
))


# ADVANCED SEARCH #

class AdvancedSearchView(GeneralView):
    def get_objects(self):
        return dict(suites_list=SUITES["all"])

# ADVANCED SEARCH (HTML)
app.add_url_rule('/advancedsearch/', view_func=AdvancedSearchView.as_view(
    'advanced_search_html',
    render_func=lambda **kwargs: render_template('advanced_search.html',
                                                 **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))

# ADVANCED SEARCH (JSON)
app.add_url_rule('/api/advancedsearch/', view_func=AdvancedSearchView.as_view(
    'advanced_search_json',
    render_func=jsonify,
    err_func=lambda e, **kwargs: deal_error(e, mode='json', **kwargs)
))


# NAVIGATION: ALL PACKAGES #

class ListpackagesView(GeneralView):
    def __init__(self, render_func=jsonify, err_func=lambda *x: x, all_=False):
        """
        the all_ parameter allows to determine if we render all results (json)
        or if we paginate them (html)
        """
        self.all_ = all_
        super(ListpackagesView, self).__init__(
            render_func=render_func, err_func=err_func)

    def get_objects(self, page=1):
        if self.all_:  # we retrieve all packages
            try:
                packages = (session.query(PackageName)
                            .order_by(PackageName.name)
                            .all()
                            )
                packages = [p.to_dict() for p in packages]
                return dict(packages=packages)
            except Exception as e:
                raise Http500Error(e)
        else:  # we paginate
            # WARNING: not serializable (TODO: serialize Pagination obj)
            try:
                offset = int(app.config.get("LIST_OFFSET") or 60)

                # we calculate the range of results
                start = (page - 1) * offset
                end = start + offset

                count_packages = (session.query(PackageName)
                                  .count()
                                  )
                packages = (session.query(PackageName)
                            .order_by(PackageName.name)
                            .slice(start, end)
                            )
                pagination = Pagination(page, offset, count_packages)

                return dict(packages=packages,
                            page=page,
                            pagination=pagination)

            except Exception as e:
                raise Http500Error(e)

# PACKAGE LISTING ROUTE (HTML)
app.add_url_rule('/list/<int:page>/', view_func=ListpackagesView.as_view(
    'listpackages_html',
    render_func=lambda **kwargs: render_template('list.html', **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))

# PACKAGE LISTING ROUTE (JSON)
app.add_url_rule('/api/list/', view_func=ListpackagesView.as_view(
    'listpackages_json',
    all_=True,  # we don't paginate json result
    render_func=jsonify,
    err_func=lambda e, **kwargs: deal_error(e, mode='json', **kwargs)
))


# NAVIGATION BY PREFIX #

class PrefixView(GeneralView):
    def get_objects(self, prefix='a'):
        """ returns the packages beginning with prefix
            and belonging to suite if specified.
        """
        prefix = prefix.lower()
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        if prefix in PackageName.get_packages_prefixes(
                app.config["CACHE_DIR"]):
            try:
                if not suite:
                    packages = (session.query(PackageName)
                                .filter(sql_func.lower(PackageName.name)
                                        .startswith(prefix))
                                .order_by(PackageName.name)
                                .all()
                                )
                else:
                    packages = (session.query(PackageName)
                                .filter(sql_func.lower(Suite.suite)
                                        == suite)
                                .filter(Suite.package_id == Package.id)
                                .filter(Package.name_id == PackageName.id)
                                .filter(sql_func.lower(PackageName.name)
                                        .startswith(prefix))
                                .order_by(PackageName.name)
                                .all()
                                )

                packages = [p.to_dict() for p in packages]
            except Exception as e:
                raise Http500Error(e)
            return dict(packages=packages,
                        prefix=prefix,
                        suite=suite)
        else:
            raise Http404Error("prefix unknown: %s" % str(prefix))


# PACKAGES LIST BY PREFIX ROUTING (HTML)
app.add_url_rule('/prefix/<prefix>/', view_func=PrefixView.as_view(
    'prefix_html',
    render_func=lambda **kwargs: render_template('prefix.html', **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))

# PACKAGES LIST BY PREFIX ROUTING (JSON)
app.add_url_rule('/api/prefix/<prefix>/', view_func=PrefixView.as_view(
    'prefix_json',
    render_func=jsonify,
    err_func=lambda e, **kwargs: deal_error(e, mode='json', **kwargs)
))


# SOURCE (packages, versions, folders, files) #

class SourceView(GeneralView):
    def _render_package(self, packagename, path_to):
        """
        renders the package page (which lists available versions)
        """
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        # we list the version with suites it belongs to
        try:
            versions_w_suites = PackageName.list_versions_w_suites(
                session, packagename, suite)
        except InvalidPackageOrVersionError:
            raise Http404Error("%s not found" % packagename)

        return dict(type="package",
                    package=packagename,
                    versions=versions_w_suites,
                    path=path_to,
                    suite=suite,
                    )

    def _render_location(self, package, version, path):
        """
        renders a location page, can be a folder or a file
        """
        try:
            location = Location(session,
                                app.config["SOURCES_DIR"],
                                app.config["SOURCES_STATIC"],
                                package, version, path)
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            raise Http404ErrorSuggestions(package, version, path)

        if location.is_symlink():
            # check if it's secure
            symlink_dest = os.readlink(location.sources_path)
            dest = os.path.normpath(  # absolute, target file
                os.path.join(os.path.dirname(location.sources_path),
                             symlink_dest))
            # note: adding trailing slash because normpath drops them
            if dest.startswith(os.path.normpath(location.version_path) + '/'):
                # symlink is safe; redirect to its destination
                return dict(redirect=os.path.normpath(
                    os.path.join(os.path.dirname(location.path_to),
                                 symlink_dest)))
            else:
                raise Http403Error(
                    'insecure symlink, pointing outside package/version/')

        if location.is_dir():  # folder, we list its content
            return self._render_directory(location)

        elif location.is_file():  # file
            return self._render_file(location)

        else:  # doesn't exist
            raise Http404Error(None)

    def _render_directory(self, location):
        """
        renders a directory, lists subdirs and subfiles
        """
        directory = Directory(location, toplevel=(location.get_path() == ""))

        # (if path == "", then the dir is toplevel, and we don't want
        # the .pc directory)

        pkg_infos = Infobox(session,
                            location.get_package(),
                            location.get_version()).get_infos()

        return dict(type="directory",
                    directory=location.get_deepest_element(),
                    package=location.get_package(),
                    content=directory.get_listing(),
                    path=location.get_path_to(),
                    pkg_infos=pkg_infos,
                    )

    def _render_file(self, location):
        """
        renders a file
        """
        file_ = SourceFile(location)

        checksum = file_.get_sha256sum(session)
        number_of_duplicates = (session.query(sql_func.count(Checksum.id))
                                .filter(Checksum.sha256 == checksum)
                                .first()[0])

        pkg_infos = Infobox(session,
                            location.get_package(),
                            location.get_version()).get_infos()

        return dict(type="file",
                    file=location.get_deepest_element(),
                    package=location.get_package(),
                    mime=file_.get_mime(),
                    raw_url=file_.get_raw_url(),
                    path=location.get_path_to(),
                    text_file=file_.istextfile(),
                    stat=location.get_stat(location.sources_path),
                    checksum=checksum,
                    number_of_duplicates=number_of_duplicates,
                    pkg_infos=pkg_infos
                    )

    def _handle_latest_version(self, package, path):
        """
        redirects to the latest version for the requested page,
        when 'latest' is provided instead of a version number
        """
        try:
            versions = PackageName.list_versions(session, package)
        except InvalidPackageOrVersionError:
            raise Http404Error("%s not found" % package)
        # the latest version is the latest item in the
        # sorted list (by debian_support.version_compare)
        version = sorted([v.version for v in versions],
                         cmp=version_compare)[-1]

        # avoids extra '/' at the end
        if path == "":
            redirect = '/'.join([package, version])
        else:
            redirect = '/'.join([package, version, path])

        # finally we tell the render function to redirect
        return dict(redirect=redirect)

    def get_objects(self, path_to):
        """
        determines if the dealing object is a package/folder/source file
        and sets this in 'type'
        Package: we want the available versions (db request)
        Directory: we want the subdirs and subfiles (disk listing)
        File: we want to render the raw url of the file
        """
        path_dict = path_to.split('/')

        if len(path_dict) == 1:  # package
            return self._render_package(path_dict[0], path_to)

        else:  # folder or file
            package = path_dict[0]
            version = path_dict[1]
            path = '/'.join(path_dict[2:])

            if version == "latest":  # we search the latest available version
                return self._handle_latest_version(package, path)
            else:
                return self._render_location(package, version, path)


def render_source_file_html(templatename, **kwargs):
    """ preprocess useful variables for the html templates """

    # if it's a redirection (e.g. triggered by /src/latest/*)
    if 'redirect' in kwargs.keys():
        return redirect(url_for('source_html',
                                path_to=kwargs['redirect']))

    if kwargs['type'] == "package":
        # we simply add pathl (for use with "You are here:")
        return render_template(
            "source_package.html",
            pathl=Location.get_path_links("source_html", kwargs['path']),
            **kwargs)

    elif kwargs['type'] == "directory":
        # we add pathl and separate files and folders
        return render_template(
            "source_folder.html",
            subdirs=filter(lambda x: x['type'] == "directory",
                           kwargs['content']),
            subfiles=filter(lambda x: x['type'] == "file", kwargs['content']),
            pathl=Location.get_path_links("source_html", kwargs['path']),
            **kwargs)
    else:  # file
        # more work to do with files

        # as long as 'lang' is in keys, then it's a text_file
        lang = None
        if 'lang' in request.args:
            lang = request.args['lang']
        # if the file is not a text file, we redirect to it
        elif not(kwargs['text_file']):
            return redirect(kwargs['raw_url'])

        sources_path = kwargs['raw_url'].replace(app.config['SOURCES_STATIC'],
                                                 app.config['SOURCES_DIR'],
                                                 1)
        # ugly, but better than global variable,
        # and better than re-requesting the db
        # TODO: find proper solution for retrieving souces_path
        # (without putting it in kwargs, we don't want it in json rendering eg)

        # we get the variables for highlighting and message (if they exist)
        try:
            highlight = request.args.get('hl')
        except (KeyError, ValueError, TypeError):
            highlight = None
        try:
            msg = request.args.get('msg')
            if msg == "":
                msg = None  # we don't want empty messages
        except (KeyError, ValueError, TypeError):
            msg = None

        # we preprocess the file with SourceCodeIterator
        sourcefile = SourceCodeIterator(
            sources_path, hl=highlight, msg=msg, lang=lang)

        return render_template(
            templatename,
            nlines=sourcefile.get_number_of_lines(),
            pathl=Location.get_path_links("source_html", kwargs['path']),
            file_language=sourcefile.get_file_language(),
            msg=sourcefile.get_msgdict(),
            code=sourcefile,
            **kwargs
            )


def render_source_file_json(**kwargs):
    # if it's a redirection (e.g. triggered by /src/latest/*)
    if 'redirect' in kwargs.keys():
        return redirect(url_for('source_json',
                                path_to=kwargs['redirect']))
    else:
        return jsonify(**kwargs)

# PACKAGE/FOLDER/FILE ROUTING (HTML)
app.add_url_rule('/src/<path:path_to>/', view_func=SourceView.as_view(
    'source_html',
    render_func=lambda **kwargs: render_source_file_html("source_file.html",
                                                         **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))

# PACKAGE/FOLDER/FILE ROUTING (JSON)
app.add_url_rule('/api/src/<path:path_to>/', view_func=SourceView.as_view(
    'source_json',
    render_func=render_source_file_json,
    err_func=lambda e, **kwargs: deal_error(e, mode='json', **kwargs)
))


# CHECKSUM REQUEST #

class ChecksumView(GeneralView):
    def __init__(self, render_func=jsonify, err_func=lambda *x: x, all_=False):
        """
        the all_ parameter allows to determine if we render all results (json)
        or if we paginate them (html)
        """
        self.all_ = all_
        super(ChecksumView, self).__init__(
            render_func=render_func, err_func=err_func)

    def get_objects(self, all=False):
        """
        Returns the files whose checksum corresponds to the one given.
        If all=True, the results aren't paginated.
        """
        try:
            page = int(request.args.get("page"))
        except:
            page = 1
        checksum = request.args.get("checksum")
        package = request.args.get("package") or None

        # we count the number of results:
        count = (session.query(sql_func.count(Checksum.id))
                 .filter(Checksum.sha256 == checksum))
        if package is not None and package != "":  # (only within the package)
            count = (count.filter(PackageName.name == package)
                     .filter(Checksum.package_id == Package.id)
                     .filter(Package.name_id == PackageName.id))
        count = count.first()[0]

        # pagination:
        if not self.all_:
            offset = int(app.config.get("LIST_OFFSET") or 60)
            start = (page - 1) * offset
            end = start + offset
            slice_ = (start, end)
            pagination = Pagination(page, offset, count)
        else:
            pagination = None
            slice_ = None

        def files_with_sum(checksum, slice_=None, package=None):
            """
            Returns a list of files whose hexdigest is checksum.
            You can slice the results, passing slice=(start, end).
            """
            results = (session.query(PackageName.name.label("package"),
                                     Package.version.label("version"),
                                     Checksum.file_id.label("file_id"),
                                     File.path.label("path"))
                       .filter(Checksum.sha256 == checksum)
                       .filter(Checksum.package_id == Package.id)
                       .filter(Checksum.file_id == File.id)
                       .filter(Package.name_id == PackageName.id)
                       )
            if package is not None and package != "":
                results = results.filter(PackageName.name == package)

            results = results.order_by("package", "version", "path")

            if slice_ is not None:
                results = results.slice(slice_[0], slice_[1])
            results = results.all()

            return [dict(path=res.path,
                         package=res.package,
                         version=res.version)
                    for res in results]

        # finally we get the files list
        results = files_with_sum(checksum, slice_=slice_, package=package)

        return dict(results=results,
                    sha256=checksum,
                    count=count,
                    page=page,
                    pagination=pagination)

# CHECKSUM REQUEST (HTML)
app.add_url_rule('/sha256/', view_func=ChecksumView.as_view(
    'checksum_html',
    render_func=lambda **kwargs: render_template("checksum.html", **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))


# CHECKSUM REQUEST (JSON)
app.add_url_rule('/api/sha256/', view_func=ChecksumView.as_view(
    'checksum_json',
    all_=True,
    render_func=jsonify,
    err_func=lambda e, **kwargs: deal_error(e, mode='json', **kwargs)
))


# CTAG REQUEST #

class CtagView(GeneralView):
    def __init__(self, render_func=jsonify, err_func=lambda *x: x, all_=False):
        """
        the all_ parameter allows to determine if we render all results (json)
        or if we paginate them (html)
        """
        self.all_ = all_
        super(CtagView, self).__init__(
            render_func=render_func, err_func=err_func)

    def get_objects(self, all=False):
        """
        Returns the places where ctag are found.
        (limit to package if package is not None)
        If all=True, the results aren't paginated.
        """
        try:
            page = int(request.args.get("page"))
        except:
            page = 1
        ctag = request.args.get("ctag")
        package = request.args.get("package") or None

        # pagination:
        if not self.all_:
            try:
                offset = int(app.config.get("LIST_OFFSET"))
            except:
                offset = 60
            start = (page - 1) * offset
            end = start + offset
            slice_ = (start, end)
        else:
            pagination = None
            slice_ = None

        (count, results) = Ctag.find_ctag(session, ctag, slice_=slice_,
                                          package=package)
        if not self.all_:
            pagination = Pagination(page, offset, count)
        else:
            pagination = None

        return dict(results=results,
                    ctag=ctag,
                    count=count,
                    page=page,
                    package=package,
                    pagination=pagination)

# CTAG REQUEST (HTML)
app.add_url_rule('/ctag/', view_func=CtagView.as_view(
    'ctag_html',
    render_func=lambda **kwargs: render_template("ctag.html", **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))


# CTAG REQUEST (JSON)
app.add_url_rule('/api/ctag/', view_func=CtagView.as_view(
    'ctag_json',
    all_=True,
    render_func=jsonify,
    err_func=lambda e, **kwargs: deal_error(e, mode='json', **kwargs)
))


# INFO PAGES #

class InfoPackageView(GeneralView):
    def get_objects(self, package, version):
        pkg_infos = Infobox(session, package, version).get_infos()
        return dict(pkg_infos=pkg_infos,
                    package=package,
                    version=version)

# INFO PER-VERSION (HTML)
app.add_url_rule('/info/package/<package>/<version>/',
                 view_func=InfoPackageView.as_view(
                     'info_package_html',
                     render_func=lambda **kwargs: render_template(
                         'infopackage.html', **kwargs),
                     err_func=lambda e, **kwargs: deal_error(
                         e, mode='html', **kwargs)
                 ))

# INFO PER-VERSION (JSON)
app.add_url_rule('/api/info/package/<package>/<version>/',
                 view_func=InfoPackageView.as_view(
                     'info_package_json',
                     render_func=jsonify,
                     err_func=lambda e, **kwargs: deal_error(e, mode='json',
                                                             **kwargs)
                 ))


# EMBEDDED PAGES #

# SOURCE FILE EMBEDDED ROUTING (HTML)
app.add_url_rule('/embed/file/<path:path_to>/', view_func=SourceView.as_view(
    'embedded_source_html',
    render_func=lambda **kwargs: render_source_file_html(
        "source_file_embedded.html", **kwargs),
    err_func=lambda e, **kwargs: deal_error(e, mode='html', **kwargs)
))


# we redirect the old used embedded file page (/embedded/<path>)
# to the new one (/embed/file/<path>)
@app.route("/embedded/<path:path_to>/")
def old_embedded_file(path_to, **kwargs):
    return redirect(url_for("embedded_source_html",
                            path_to=path_to,
                            **request.args))

# INFO PER-VERSION (EMBEDDED HTML)
app.add_url_rule('/embed/pkginfo/<package>/<version>/',
                 view_func=InfoPackageView.as_view(
                     'embedded_info_package_html',
                     render_func=lambda **kwargs: render_template(
                         'infopackage_embed.html', **kwargs),
                     err_func=lambda e, **kwargs: deal_error(
                         e, mode='html', **kwargs)
                 ))


# STATISTICS #

class StatsView(GeneralView):
    def get_objects(self, suite):
        if suite not in statistics.suites(session, 'all'):
            raise Http404Error()  # security, to avoid suite='../../foo',
            # to include <img>s, etc.

        stats_file = os.path.join(app.config["CACHE_DIR"], "stats.data")
        res = extract_stats(filename=stats_file,
                            filter_suites=["debian_" + suite])

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    suite=suite)

# STATS FOR ONE SUITE (HTML)
app.add_url_rule('/stats/<suite>/',
                 view_func=StatsView.as_view(
                     'stats_html',
                     render_func=lambda **kwargs: render_template(
                         'stats_suite.html', **kwargs),
                     err_func=lambda e, **kwargs: deal_error(
                         e, mode='html', **kwargs)
                 ))

# STATS FOR ONE SUITE (JSON)
app.add_url_rule('/api/stats/<suite>/',
                 view_func=StatsView.as_view(
                     'stats_json',
                     render_func=jsonify,
                     err_func=lambda e, **kwargs: deal_error(
                         e, mode='json', **kwargs)
                 ))


class AllStatsView(GeneralView):
    def get_objects(self):
        stats_file = os.path.join(app.config["CACHE_DIR"], "stats.data")
        res = extract_stats(filename=stats_file)

        all_suites = ["debian_" + x for x in
                      statistics.suites(session, suites='all')]
        release_suites = ["debian_" + x for x in
                          statistics.suites(session, suites='release')]
        devel_suites = ["debian_" + x for x in
                        statistics.suites(session, suites='devel')]

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    all_suites=all_suites,
                    release_suites=release_suites,
                    devel_suites=devel_suites)

# STATS FOR ALL SUITES (HTML)
app.add_url_rule('/stats/',
                 view_func=AllStatsView.as_view(
                     'stats_all_html',
                     render_func=lambda **kwargs: render_template(
                         'stats_all_suites.html', **kwargs),
                     err_func=lambda e, **kwargs: deal_error(
                         e, mode='html', **kwargs)
                 ))

# STATS FOR ALL SUITES (JSON)
app.add_url_rule('/api/stats/',
                 view_func=AllStatsView.as_view(
                     'stats_all_json',
                     render_func=jsonify,
                     err_func=lambda e, **kwargs: deal_error(
                         e, mode='json', **kwargs)
                 ))
