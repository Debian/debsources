import os

from flask import current_app

from ..helper import bind_render
from ..views import (
    IndexView, DocView, AboutView, SearchView, CtagView, ChecksumView,
    PrefixView, ListPackagesView, InfoPackageView, Ping, ErrorHandler)

from .views import StatsView, SourceView

from . import bp_sources

# context vars
@bp_sources.context_processor
def skeleton_variables():
    site_name = bp_sources.name
    return dict(site_name=site_name,)


# site errors
# 500 handler cannot be registered on a blueprint
bp_sources.errorhandler(403)(
        lambda e: (ErrorHandler(bp_name='sources')(e, http=403), 403))
bp_sources.errorhandler(404)(
        lambda e: (ErrorHandler(bp_name='sources')(e, http=404), 404))


# ping service
bp_sources.add_url_rule(
        '/api/ping/',
        view_func=Ping.as_view(
            'ping',))


# INDEXVIEW
bp_sources.add_url_rule(
    '/',
    view_func=IndexView.as_view(
        'index',
        render_func=bind_render('sources/index.html'),
        news_html='sources_news.html'))


# DOCVIEW
bp_sources.add_url_rule(
    '/doc/',
    view_func=DocView.as_view(
        'doc',
        render_func=bind_render('sources/doc.html'),))


bp_sources.add_url_rule(
    '/doc/url/',
    view_func=DocView.as_view(
        'doc_url',
        render_func=bind_render('sources/doc_url.html'),))


bp_sources.add_url_rule(
    '/doc/api/',
    view_func=DocView.as_view(
        'doc_api',
        render_func=bind_render('sources/doc_api.html'),))


bp_sources.add_url_rule(
    '/doc/overview',
    view_func=DocView.as_view(
        'doc_overview',
        render_func=bind_render('sources/doc_overview.html'),))


# ABOUTVIEW
bp_sources.add_url_rule(
    '/about/',
    view_func=AboutView.as_view(
        'about',
        render_func=bind_render('sources/about.html'),))


# STATSVIEW
bp_sources.add_url_rule(
    '/stats/',
    view_func=StatsView.as_view(
        'stats',
        render_func=bind_render('sources/stats.html'),
        err_func=ErrorHandler('sources'),
        get_objects='stats',))


# api
bp_sources.add_url_rule(
    '/api/stats/',
    view_func=StatsView.as_view(
        'api_stats',
        err_func=ErrorHandler(mode='json')))


bp_sources.add_url_rule(
    '/stats/<suite>/',
    view_func=StatsView.as_view(
        'stats_suite',
        render_func=bind_render('sources/stats_suite.html'),
        err_func=ErrorHandler('sources'),
        get_objects='stats_suite',))


# api
bp_sources.add_url_rule(
    '/api/stats/<suite>/',
    view_func=StatsView.as_view(
        'api_stats_suite',
        err_func=ErrorHandler(mode='json'),
        get_objects='stats_suite'))


# SEARCHVIEW
bp_sources.add_url_rule(
    '/search/',
    view_func=SearchView.as_view(
        'recv_search',
        render_func=bind_render('sources/index.html'),
        recv_search=True),
    methods=['GET', 'POST'])


bp_sources.add_url_rule(
    '/advancedsearch/',
    view_func=SearchView.as_view(
        'advanced_search',
        render_func=bind_render('sources/search_advanced.html'),
        err_func=ErrorHandler('sources'),
        get_objects='advanced',))


# api
bp_sources.add_url_rule(
    '/api/advancedsearch/',
    view_func=SearchView.as_view(
        'api_advanced_search',
        err_func=ErrorHandler(mode='json')))



bp_sources.add_url_rule(
    '/search/<query>',
    view_func=SearchView.as_view(
        'search',
        render_func=bind_render('sources/search.html'),
        err_func=ErrorHandler('sources'),
        get_objects='query',))


# api
bp_sources.add_url_rule(
    '/api/search/<query>/',
    view_func=SearchView.as_view(
        'api_search',
        err_func=ErrorHandler(mode='json')))


# ChecksumView
bp_sources.add_url_rule(
    '/sha256/',
    view_func=ChecksumView.as_view(
        'checksum',
        render_func=bind_render('sources/checksum.html'),
        err_func=ErrorHandler('sources'),
        pagination=True))


# api
bp_sources.add_url_rule(
    '/api/sha256/',
    view_func=ChecksumView.as_view(
        'api_checksum',
        err_func=ErrorHandler(mode='json')))


# CtagView
bp_sources.add_url_rule(
    '/ctag/',
    view_func=CtagView.as_view(
        'ctag',
        render_func=bind_render('sources/ctag.html'),
        err_func=ErrorHandler('sources'),
        pagination=True))


# api
bp_sources.add_url_rule(
    '/api/ctag/',
    view_func=CtagView.as_view(
        'api_ctag',
        err_func=ErrorHandler(mode='json')))


# PREFIXVIEW
bp_sources.add_url_rule(
    '/prefix/<prefix>',
    view_func=PrefixView.as_view(
        'prefix',
        render_func=bind_render('sources/prefix.html'),
        err_func=ErrorHandler('sources'),))


# api
bp_sources.add_url_rule(
    '/api/prefix/<prefix>/',
    view_func=PrefixView.as_view(
        'api_prefix',
        err_func=ErrorHandler(mode='json')))


# LISTPACKAGESVIEW
bp_sources.add_url_rule(
    '/list/<int:page>',
    view_func=ListPackagesView.as_view(
        'list_packages',
        render_func=bind_render('sources/list.html'),
        err_func=ErrorHandler('sources'),
        pagination=True))


# api
bp_sources.add_url_rule(
    '/api/list/',
    view_func=ListPackagesView.as_view(
        'api_list_packages',
        err_func=ErrorHandler(mode='json')))


# SOURCEVIEW
bp_sources.add_url_rule(
    '/src/<path:path_to>/',
    view_func=SourceView.as_view(
        'source',
        # the render func is set by the views.
        err_func=ErrorHandler('sources'),
        templatename='sources/source_file.html'))


# api
bp_sources.add_url_rule(
    '/api/src/<path:path_to>/',
    view_func=SourceView.as_view(
        'api_source',
        err_func=ErrorHandler(mode='json'),
        api=True))


# SOURCE FILE EMBEDDED ROUTING
bp_sources.add_url_rule(
    '/embed/file/<path:path_to>/',
    view_func=SourceView.as_view(
        'embedded_source',
        err_func=ErrorHandler('sources'),
        templatename="source_file_embedded.html"))


# we redirect the old used embedded file page (/embedded/<path>)
# to the new one (/embed/file/<path>)
@bp_sources.route("/embedded/<path:path_to>/")
def old_embedded_file(path_to, **kwargs):
    return redirect(url_for(".embedded_source",
                            path_to=path_to,
                            **request.args))


# INFO PER-VERSION
bp_sources.add_url_rule(
    '/info/package/<package>/<version>/',
    view_func=InfoPackageView.as_view(
        'info_package',
        render_func=bind_render('sources/infopackage.html'),
        err_func=ErrorHandler('sources'),))


# api
bp_sources.add_url_rule(
    '/api/info/package/<package>/<version>/',
    view_func=InfoPackageView.as_view(
        'api_info_package',
        err_func=ErrorHandler(mode='json')))



# INFO PER-VERSION (EMBEDDED)
bp_sources.add_url_rule(
    '/embed/pkginfo/<package>/<version>/',
    view_func=InfoPackageView.as_view(
        'sources/embedded_info_package_html',
        render_func=bind_render('sources/infopackage_embed.html'),
        err_func=ErrorHandler('sources')))
