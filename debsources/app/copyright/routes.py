# Copyright (C) 2015  The Debsources developers <info@sources.debian.net>.
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


from flask import jsonify

from ..helper import bind_render
from . import bp_copyright
from ..views import (IndexView, PrefixView, ListPackagesView, ErrorHandler,
                     Ping, PackageVersionsView)
from .views import LicenseView, ChecksumLicenseView


# context vars
@bp_copyright.context_processor
def skeleton_variables():
    site_name = bp_copyright.name
    return dict(site_name=site_name,)


# 403 and 404 errors
bp_copyright.errorhandler(403)(
    lambda e: (ErrorHandler()(e, http=403), 403))
bp_copyright.errorhandler(404)(
    lambda e: (ErrorHandler()(e, http=404), 404))


# INDEXVIEW
bp_copyright.add_url_rule(
    '/',
    view_func=IndexView.as_view(
        'index',
        render_func=bind_render('copyright/index.html'),
        err_func=ErrorHandler('copyright'),
        news_html='copyright_news.html'))

# ping service
bp_copyright.add_url_rule(
    '/api/ping/',
    view_func=Ping.as_view(
        'ping',))


# PREFIXVIEW
bp_copyright.add_url_rule(
    '/prefix/<prefix>/',
    view_func=PrefixView.as_view(
        'prefix',
        render_func=bind_render('prefix.html'),
        err_func=ErrorHandler('copyright'),))


# api
bp_copyright.add_url_rule(
    '/api/prefix/<prefix>/',
    view_func=PrefixView.as_view(
        'api_prefix',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json')))


# LISTPACKAGESVIEW
bp_copyright.add_url_rule(
    '/list/<int:page>/',
    view_func=ListPackagesView.as_view(
        'list_packages',
        render_func=bind_render('list.html'),
        err_func=ErrorHandler('copyright'),
        pagination=True))


# api
bp_copyright.add_url_rule(
    '/api/list/',
    view_func=ListPackagesView.as_view(
        'api_list_packages',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json')))


# VERSIONSVIEW
bp_copyright.add_url_rule(
    '/license/<string:packagename>/',
    view_func=PackageVersionsView.as_view(
        'versions',
        render_func=bind_render('copyright/package.html'),
        err_func=ErrorHandler('copyright')))

# api
bp_copyright.add_url_rule(
    '/api/license/<string:packagename>/',
    view_func=PackageVersionsView.as_view(
        'api_cp_versions',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json')))

# LICENSEVIEW
bp_copyright.add_url_rule(
    '/license/<path:path_to>/',
    view_func=LicenseView.as_view(
        'license',
        render_func=bind_render('copyright/license.html'),
        err_func=ErrorHandler('copyright')))

# CHECKSUM VIEW

# api
bp_copyright.add_url_rule(
    '/api/sha256/',
    view_func=ChecksumLicenseView.as_view(
        'api_checksum',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json')))
