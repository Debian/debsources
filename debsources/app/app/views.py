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

from flask import jsonify, render_template, request, url_for
from flask.views import View

from debsources.excepts import (
    InvalidPackageOrVersionError, FileOrFolderNotFound,
    Http500Error, Http404Error, Http404ErrorSuggestions, Http403Error)
from debsources.models import (
    Ctag, Package, PackageName, Checksum, Location, Directory,
    SourceFile, File, Suite)
from debsources.sqla_session import _close_session
from debsources import local_info
# XXX from the original apps
from debsources.app.forms import SearchForm

from debsources.app import app_wrapper
app = app_wrapper.app
session = app_wrapper.session


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

    def __init__(self, bp_name='', mode='html'):
        self.mode = mode
        self.bp_name = bp_name

    def __call__(self, error, http=404):
        try:
            method = getattr(self, 'error_{}'.format(http))
        except:
            raise Exception("Unimplemented HTTP error: {}".format(http))
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
                self.bp_path(self.bp_name, '500.html')), 500


# XXX blueprints will have its own error handler
app.errorhandler(403)(lambda _: ("Forbidden", 403))
app.errorhandler(404)(lambda _: ("File not Found", 404))
app.errorhandler(500)(lambda _: ("Server Error", 500))


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
