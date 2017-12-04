# Copyright (C) 2015  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
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


from flask import jsonify, request, render_template

from ..helper import bind_render, generic_before_request
from . import bp_copyright
from ..views import (IndexView, PrefixView, ListPackagesView, ErrorHandler,
                     Ping, PackageVersionsView, SearchView, NewsArchiveView)
from .views import LicenseView, ChecksumLicenseView, SearchFileView, StatsView
from debsources.excepts import Http404Error


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


# Before request
@bp_copyright.before_request
def before_request():
    endpoints = ['license', 'file', 'api_file']
    if request.endpoint.replace('copyright.', '', 1) in endpoints:
        try:
            return generic_before_request(request, 3)
        except Http404Error:
            return render_template('404.html'), 404

# INDEXVIEW
bp_copyright.add_url_rule(
    '/',
    view_func=IndexView.as_view(
        'index',
        render_func=bind_render('copyright/index.html'),
        err_func=ErrorHandler('copyright'),
        news_html='copyright_news.html',
        news_archive_html='copyright_news_archive.html'))


# NEWSARCHIVEVIEW
bp_copyright.add_url_rule(
    '/news_archive',
    view_func=NewsArchiveView.as_view(
        'news_archive',
        render_func=bind_render('news_archive.html'),
        err_func=ErrorHandler('copyright'),
        news_archive_html='copyright_news_archive.html'))

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
    '/license/<string:packagename>/<string:version>/',
    view_func=LicenseView.as_view(
        'license',
        render_func=bind_render('copyright/license.html'),
        err_func=ErrorHandler('copyright')))

# CHECKSUM VIEW

bp_copyright.add_url_rule(
    '/sha256/',
    view_func=ChecksumLicenseView.as_view(
        'checksum',
        render_func=bind_render('copyright/checksum.html'),
        err_func=ErrorHandler('copyright'),
        pagination=True))

# api
bp_copyright.add_url_rule(
    '/api/sha256/',
    view_func=ChecksumLicenseView.as_view(
        'api_checksum',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json')),
    methods=('GET', 'POST'))


# FileSearch VIEW

bp_copyright.add_url_rule(
    '/file/<string:packagename>/<string:version>/<path:path_to>/',
    view_func=SearchFileView.as_view(
        'file',
        render_func=bind_render('copyright/file.html'),
        err_func=ErrorHandler('copyright')))

# api
bp_copyright.add_url_rule(
    '/api/file/<string:packagename>/<string:version>/<path:path_to>/',
    view_func=SearchFileView.as_view(
        'api_file',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json')))

# SEARCHVIEW
bp_copyright.add_url_rule(
    '/search/',
    view_func=SearchView.as_view(
        'recv_search',
        render_func=bind_render('copyright/index.html'),
        err_func=ErrorHandler('copyright'),
        recv_search=True),
    methods=['GET', 'POST'])


bp_copyright.add_url_rule(
    '/search/<query>/',
    view_func=SearchView.as_view(
        'search',
        render_func=bind_render('search.html'),
        err_func=ErrorHandler('copyright'),
        get_objects='query',))


# api
bp_copyright.add_url_rule(
    '/api/search/<query>/',
    view_func=SearchView.as_view(
        'api_search',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json'),
        get_objects='query'))

# STATSVIEW
bp_copyright.add_url_rule(
    '/stats/',
    view_func=StatsView.as_view(
        'stats',
        render_func=bind_render('copyright/stats.html'),
        err_func=ErrorHandler('copyright'),
        get_objects='stats',))

# api
bp_copyright.add_url_rule(
    '/api/stats/',
    view_func=StatsView.as_view(
        'api_stats',
        err_func=ErrorHandler(mode='json'),
        get_objects='stats',))


bp_copyright.add_url_rule(
    '/stats/<suite>/',
    view_func=StatsView.as_view(
        'stats_suite',
        render_func=bind_render('copyright/stats_suite.html'),
        err_func=ErrorHandler('copyright'),
        get_objects='stats_suite',))


# api
bp_copyright.add_url_rule(
    '/api/stats/<suite>/',
    view_func=StatsView.as_view(
        'api_stats_suite',
        render_func=jsonify,
        err_func=ErrorHandler(mode='json'),
        get_objects='stats_suite'))
