# Copyright (C) 2013-2014  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

from __future__ import absolute_import

# XXX copied from app/views.py

import os
import six

from debian.debian_support import version_compare

from flask import (
    current_app, jsonify, render_template, request, url_for, redirect)
from flask.views import View

from debsources.excepts import (
    Http500Error, Http404Error, Http404ErrorSuggestions, Http403Error,
    InvalidPackageOrVersionError)
from debsources.models import Package, SuiteAlias
import debsources.query as qry
from debsources.sqla_session import _close_session
from debsources import local_info
from debsources.consts import SUITES

from .forms import SearchForm
from .pagination import Pagination
from .infobox import Infobox
from .helper import (format_big_num, url_for_other_page,
                     bind_redirect)
from . import app_wrapper
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

    packages_prefixes = qry.pkg_names_get_packages_prefixes(
        app.config["CACHE_DIR"])

    credits_file = os.path.join(app.config["LOCAL_DIR"], "credits.html")
    credits = local_info.read_html(credits_file)

    return dict(packages_prefixes=packages_prefixes,
                searchform=SearchForm(),
                last_update=last_update,
                credits=credits,
                name=app.import_name)


# jinja2 settings
app.jinja_env.filters['format_big_num'] = format_big_num
app.jinja_env.globals['url_for_other_page'] = url_for_other_page


# ERRORS
class ErrorHandler(object):

    def __init__(self, mode='html', http=404):
        self.mode = mode
        self.http = http

    def __call__(self, error, http=None):
        if http is not None:
            self.http = http
        try:
            method = getattr(self, 'error_{}'.format(self.http))
        except:
            raise Exception("Unimplemented HTTP error: {}".format(self.http))
        return method(error)

    def error_403(self, error):
        if self.mode == 'json':
            return jsonify(dict(error=403))
        else:
            return render_template('403.html'), 403

    def error_404(self, error):
        if self.mode == 'json':
            return jsonify(dict(error=404))
        else:
            if isinstance(error, Http404ErrorSuggestions):
                # let's suggest all the possible locations with a different
                # package version
                possible_versions = qry.pkg_names_list_versions(
                    session, error.package)
                suggestions = ['/'.join(
                    [_f for _f in [error.package, v.version, error.path]
                     if _f])
                    for v in possible_versions]
                return render_template('404_suggestions.html',
                                       suggestions=suggestions), 404
            else:
                return render_template('404.html'), 404

    def error_500(self, error):
        """
        logs a 500 error and returns the correct template
        """
        app.logger.exception(error)

        if self.mode == 'json':
            return jsonify(dict(error=500))
        else:
            return render_template('500.html'), 500


# TODO unlike 403,404, which could be registered per blueprint,
# there could be only one 500 error handler for the whole app.
# thus, the 500 handler should be aware of the active blueprint,
# so that correct page template will be rendered for the blueprint.
# we should avoid hard-coding the 'source'
app.errorhandler(500)(ErrorHandler(http=500))

# following is a plain text, bp-agnostic one.
# app.errorhandler(403)(lambda _: ("Forbidden", 403))
# app.errorhandler(404)(lambda _: ("File not Found", 404))
# app.errorhandler(500)(lambda _: ("Server Error", 500))


# FOR BOTH RENDERING AND API
class GeneralView(View):
    def __init__(self,
                 render_func=jsonify,
                 err_func=ErrorHandler(mode='json'),
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
            if isinstance(get_objects, six.string_types):
                self.get_objects = getattr(self, "get_" + get_objects)
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
        except Http403Error as e:
            return self.err_func(e, http=403)
        except Http404Error as e:
            return self.err_func(e, http=404)
        except Http500Error as e:
            return self.err_func(e, http=500)
        # do not propagate the exception
        except Exception as e:
            return self.err_func(e, http=500)

    def _redirect_to_url(self, endpoint, redirect_url, redirect_code=301):
        if endpoint == '.versions':
            self.render_func = bind_redirect(url_for(endpoint,
                                             packagename=redirect_url),
                                             code=redirect_code)
        else:
            self.render_func = bind_redirect(url_for(endpoint,
                                             path_to=redirect_url),
                                             code=redirect_code)
        return dict(redirect=redirect_url)

    def _handle_latest_version(self, endpoint, package, path):
        """
        redirects to the latest version for the requested page,
        when 'latest' is provided instead of a version number
        """
        try:
            versions = qry.pkg_names_list_versions(session, package)
        except InvalidPackageOrVersionError:
            raise Http404Error("%s not found" % package)
        # the latest version is the latest item in the
        # sorted list (by debian_support.version_compare)
        version = sorted([v.version for v in versions],
                         cmp=version_compare)[-1]

        # avoids extra '/' at the end
        if path == "":
            redirect_url = '/'.join([package, version])
        else:
            redirect_url = '/'.join([package, version, path])

        return self._redirect_to_url(endpoint, redirect_url)

    def handle_versions(self, version, package, path):
        check_for_alias = session.query(SuiteAlias) \
            .filter(SuiteAlias.alias == version).first()
        if check_for_alias:
                version = check_for_alias.suite
        try:
                versions_w_suites = qry.pkg_names_list_versions_w_suites(
                    session, package)
        except InvalidPackageOrVersionError:
                raise Http404Error("%s not found" % package)

        versions = sorted([v['version'] for v in versions_w_suites
                          if version in v['suites']],
                          cmp=version_compare)
        return versions


# PING #
# this is used to check the health of the service
# for example by codesearch.debian.net
# If we want to stop traffic from codesearch.d.n, just return 500 error
class Ping(View):
    def dispatch_request(self):
        update_ts_file = os.path.join(
            current_app.config['CACHE_DIR'], 'last-update')
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
                exact_matching = qry.get_pkg_by_name(session, query)

                other_results = qry.get_pkg_by_similar_name(session, query)
            except Exception as e:
                raise Http500Error(e)  # db problem, ...
        else:
            try:
                exact_matching = qry.get_pkg_by_name(session, query, suite)

                other_results = qry.get_pkg_by_similar_name(session,
                                                            query, suite)
            except Exception as e:
                raise Http500Error(e)  # db problem, ...

        if exact_matching is not None:
            exact_matching = exact_matching.to_dict()
        if other_results is not None:
            other_results = [o.to_dict() for o in other_results]
            # we exclude the 'exact' matching from other_results:
            other_results = [x for x in other_results if x != exact_matching]

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
    def _files_with_sum(checksum, slice_=None, package=None, suite=None):
        """
        Returns a list of files whose hexdigest is checksum.
        You can slice the results, passing slice=(start, end).
        """
        results = qry.get_files_by_checksum(session, checksum, package, suite)

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
        count = qry.count_files_checksum(session, checksum, package)
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
        results = self._files_with_sum(
            checksum, slice_=slice_, package=package)

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

        (count, results) = qry.find_ctag(session, ctag, slice_=slice_,
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
        if prefix in qry.pkg_names_get_packages_prefixes(
                app.config["CACHE_DIR"]):
            try:
                if not suite:
                    packages = qry.get_pkg_filter_prefix(session,
                                                         prefix).all()
                else:
                    packages = qry.get_pkg_filter_prefix(session,
                                                         prefix,
                                                         suite).all()

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
                packages = qry.get_all_packages(session).all()
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

                count_packages = qry.count_packages(session)
                packages = (qry.get_all_packages(session)
                            .slice(start, end)
                            )
                pagination = Pagination(page, offset, count_packages)

                return dict(packages=packages,
                            page=page,
                            pagination=pagination)

            except Exception as e:
                raise Http500Error(e)


class PackageVersionsView(GeneralView):
    def get_objects(self, packagename):
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        # we list the version with suites it belongs to
        try:
            versions_w_suites = qry.pkg_names_list_versions_w_suites(
                session, packagename, suite, reverse=True)
        except InvalidPackageOrVersionError:
            raise Http404Error("%s not found" % packagename)

        # we simply add pathl (for use with "You are here:")
        if request.blueprint == 'sources':
            endpoint = '.source'
        elif request.blueprint == 'copyright':
            endpoint = '.license'

        pathl = qry.location_get_path_links(endpoint, packagename)

        return dict(type="package",
                    package=packagename,
                    versions=versions_w_suites,
                    path=packagename,
                    suite=suite,
                    pathl=pathl
                    )


# INFO PAGES #
class InfoPackageView(GeneralView):
    def get_objects(self, package, version):
        pkg_infos = Infobox(session, package, version).get_infos()
        return dict(pkg_infos=pkg_infos,
                    package=package,
                    version=version)
