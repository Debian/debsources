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

# XXX copied from app/views.py

import os

from flask import (
    current_app, jsonify, render_template, request, url_for, redirect)
from flask.views import View

from sqlalchemy import func as sql_func

from debsources.excepts import (
    InvalidPackageOrVersionError, FileOrFolderNotFound,
    Http500Error, Http404Error, Http404ErrorSuggestions, Http403Error)
from debsources.models import (
    Ctag, Package, PackageName, Checksum, Location, Directory,
    SourceFile, File, Suite)
from debsources.sqla_session import _close_session
from debsources import local_info
from debsources.consts import SUITES
# XXX from the original apps
from debsources.app.forms import SearchForm
from debsources.app.pagination import Pagination

from debsources.app import app_wrapper
app = app_wrapper.app
session = app_wrapper.session


# static file serving
if 'SERVE_STATIC_FILES' in app.config and app.config['SERVE_STATIC_FILES']:
    import flask

    @app.route('/javascript/<path:path>')
    def javascript(path):
        return flask.send_from_directory('/usr/share/javascript/', path)

    @app.route('/icons/<path:path>')
    def icons(path):
        return flask.send_from_directory('/usr/share/icons/', path)


@app.teardown_appcontext
def shutdown_session(exception=None):
    _close_session(session)


# variables needed by "base.html" skeleton
# packages_prefixes and search form (for the left menu),
# last_update (for the footer)
# TODO the context need a little bit modification
@app.context_processor
def skeleton_variables():
    update_ts_file = os.path.join(app.config['CACHE_DIR'], 'last-update')
    # TODO, this part should be moved to per blueprint context processor
    last_update = local_info.read_update_ts(update_ts_file)

    packages_prefixes = PackageName.get_packages_prefixes(
        app.config["CACHE_DIR"])

    credits_file = os.path.join(app.config["LOCAL_DIR"], "credits.html")
    credits = local_info.read_html(credits_file)

    return dict(packages_prefixes=packages_prefixes,
                searchform=SearchForm(),
                last_update=last_update,
                credits=credits)


# jinja settings
def format_big_num(num):
    try:
        res = "{:,}".format(num)
    except:
        res = num
    return res

app.jinja_env.filters['format_big_num'] = format_big_num


def url_for_other_page(page):
    args = dict(request.args.copy())
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page
# end jinja settings


# ERRORS
class ErrorHandler(object):

    def __init__(self, bp_name='', mode='html', http=404):
        self.mode = mode
        self.bp_name = bp_name
        self.http = http

    def __call__(self, error, http=None):
        if http is not None:
            self.http = http
        try:
            method = getattr(self, 'error_{}'.format(self.http))
        except:
            raise Exception("Unimplemented HTTP error: {}".format(self.http))
        return method(error)

    def bp_path(self, tpl):
        return os.path.join(self.bp_name, tpl)

    def error_403(self, error):
        if self.mode == 'json':
            return jsonify(dict(error=403))
        else:
            return render_template(self.bp_path('403.html')), 403

    def error_404(self, error):
        if self.mode == 'json':
            return jsonify(dict(error=404))
        else:
            if isinstance(error, Http404ErrorSuggestions):
                # let's suggest all the possible locations with a different
                # package version
                possible_versions = PackageName.list_versions(
                    session, error.package)
                suggestions = ['/'.join(
                    filter(None, [error.package, v.version, error.path]))
                    for v in possible_versions]
                return render_template(self.bp_path('404_suggestions.html'),
                                       suggestions=suggestions), 404
            else:
                return render_template(self.bp_path('404.html')), 404

    def error_500(self, error):
        """
        logs a 500 error and returns the correct template
        """
        app.logger.exception(error)

        if self.mode == 'json':
            return jsonify(dict(error=500))
        else:
            return render_template(
                self.bp_path('500.html')), 500


# TODO blueprints should have its own error handler
# this indicates, at least for the 500 internal errorhandler,
# which could only be set under application context under flask,
# should be aware of which bp is active.
#
# app.errorhandler(403)(lambda _: ("Forbidden", 403))
# app.errorhandler(404)(lambda _: ("File not Found", 404))
# app.errorhandler(500)(lambda _: ("Server Error", 500))
app.errorhandler(403)(ErrorHandler('sources', http=403))
app.errorhandler(404)(ErrorHandler('sources', http=404))
app.errorhandler(500)(ErrorHandler('sources', http=500))


# FOR BOTH RENDERING AND API
class GeneralView(View):
    def __init__(self,
                 render_func=jsonify,
                 err_func=lambda *args, **kwargs: "OOPS! Error occurred.",
                 get_objects=None,
                 **kwargs):
        """
        render_func: the render function, e.g. jsonify or render_template
        err_func: the function called when an error occurs
        get_objects: the function called to get context objects.
        """
        self.render_func = render_func
        self.err_func = err_func

        if get_objects:
            if isinstance(get_objects, basestring):
                self.get_objects = getattr(self, "get_"+get_objects)
            else:
                # we don't check if it's a callable.
                # if err, then let it err.
                self.get_objects = get_objects

        self.d = kwargs

    def get_objects(self, **kwargs):
        return dict()

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


# PING #
# this is used to check the health of the service
# for example by codesearch.debian.net
# If we want to stop traffic from codesearch.d.n, just return 500 error
class Ping(View):
    def dispatch_request(self):
        update_ts_file = os.path.join(current_app.config['CACHE_DIR'], 'last-update')
        last_update = local_info.read_update_ts(update_ts_file)
        try:
            session.query(Package).first().id  # database check
        except:
            return jsonify(dict(status="db error", http_status_code=500)), 500
        return jsonify(dict(status="ok",
                            http_status_code=200,
                            last_update=last_update))


# for '/'
class IndexView(GeneralView):

    def get_objects(self, **kwargs):
        news_file = os.path.join(current_app.config["LOCAL_DIR"],
                                 self.d['news_html'])
        news = local_info.read_html(news_file)
        return dict(news=news)


# for /docs/*
class DocView(GeneralView):
    """
    Renders page for /doc/*
    """


# for /about/
class AboutView(GeneralView):
    """
    Renders page for /about/
    """


class SearchView(GeneralView):

    def dispatch_request(self, **kwargs):
        if self.d.get('recv_search'):
            return self.recv_search()
        else:
            return super(SearchView, self).dispatch_request(**kwargs)

    def get_query(self, query=''):
        """
        processes the search query and renders the results in a dict
        """
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

        query = query.replace('%', '').replace('_', '')
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""

        try:
            exact_matching, other_results = q.search_query(
                session, query, suite)
        except Exception as e:
            raise HTTP500Error(e)  # db problem, ...

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

    def get_advanced(self):
        return dict(suites_list=SUITES["all"])

    # for '/search/'
    def recv_search(self, **kwargs):
        searchform = SearchForm(request.form)
        if searchform.validate_on_submit():
            params = dict(query=searchform.query.data)
            suite = searchform.suite.data
            if suite:
                params["suite"] = suite
            return redirect(url_for(".search", **params))
        else:
            # we return the form, to display the errors
            return self.render_func(searchform=searchform)


class ChecksumView(GeneralView):

    @staticmethod
    def _files_with_sum(checksum, slice_=None, package=None):
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


    def get_objects(self, **kwargs):
        """
        Returns the files whose checksum corresponds to the one given.
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
        if self.d.get('pagination'):
            offset = int(current_app.config.get("LIST_OFFSET") or 60)
            start = (page - 1) * offset
            end = start + offset
            slice_ = (start, end)
            pagination = Pagination(page, offset, count)
        else:
            pagination = None
            slice_ = None

        # finally we get the files list
        results = self._files_with_sum(checksum, slice_=slice_, package=package)

        return dict(results=results,
                    sha256=checksum,
                    count=count,
                    page=page,
                    pagination=pagination)


class CtagView(GeneralView):

    def get_objects(self):
        """
        Returns the places where ctag are found.
        (limit to package if package is not None)
        """
        try:
            page = int(request.args.get("page"))
        except:
            page = 1
        ctag = request.args.get("ctag")
        package = request.args.get("package") or None

        # pagination:
        if self.d.get('pagination'):
            try:
                offset = int(current_app.config.get("LIST_OFFSET"))
            except:
                offset = 60
            start = (page - 1) * offset
            end = start + offset
            slice_ = (start, end)
        else:
            pagination = None
            slice_ = None
        count, results = Ctag.find_ctag(session, ctag, slice_=slice_,
                                          package=package)
        if self.d.get('pagination'):
            pagination = Pagination(page, offset, count)
        else:
            pagination = None

        return dict(results=results,
                    ctag=ctag,
                    count=count,
                    page=page,
                    package=package,
                    pagination=pagination)


class PrefixView(GeneralView):

    def get_objects(self, prefix='a'):
        """
        returns the packages beginning with prefix
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


class ListPackagesView(GeneralView):
    def get_objects(self, page=1):
        if not self.d.get('pagination'):  # api form, we retrieve all packages
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


# INFO PAGES #
class InfoPackageView(GeneralView):
    def get_objects(self, package, version):
        pkg_infos = Infobox(session, package, version).get_infos()
        return dict(pkg_infos=pkg_infos,
                    package=package,
                    version=version)
