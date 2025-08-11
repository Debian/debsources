# Copyright (C) 2013-2021  The Debsources developers
# <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


from flask import current_app, jsonify, render_template, request

from debsources.excepts import Http404Error

from ..helper import bind_render, generic_before_request
from ..views import (
    ChecksumView,
    CtagView,
    ErrorHandler,
    IndexView,
    InfoPackageView,
    ListPackagesView,
    NewsArchiveView,
    PackageVersionsView,
    Ping,
    PrefixView,
    SearchView,
)
from . import bp_sources
from .views import SourceView, StatsView


# context vars
@bp_sources.context_processor
def skeleton_variables():
    site_name = bp_sources.name
    return dict(
        site_name=site_name,
    )


# site errors
# XXX 500 handler cannot be registered on a blueprint
# TODO see debsources.app.view#errorhandler section
bp_sources.errorhandler(403)(lambda e: (ErrorHandler()(e, http=403), 403))
bp_sources.errorhandler(404)(lambda e: (ErrorHandler()(e, http=404), 404))


# Before request
@bp_sources.before_request
def before_request():
    try:
        if "embedded" in request.endpoint:
            return generic_before_request(current_app.session, request, 3)
        elif "source" in request.endpoint.split(".")[1]:
            return generic_before_request(current_app.session, request, 2)
    except Http404Error:
        return render_template("404.html"), 404


# ping service
bp_sources.add_url_rule(
    "/api/ping/",
    view_func=Ping.as_view(
        "ping",
    ),
)


# INDEXVIEW
bp_sources.add_url_rule(
    "/",
    view_func=IndexView.as_view(
        "index",
        render_func=bind_render("sources/index.html"),
        err_func=ErrorHandler("sources"),
        news_html="sources_news.html",
        news_archive_html="sources_news_archive.html",
    ),
)


# NEWSARCHIVEVIEW
bp_sources.add_url_rule(
    "/news_archive",
    view_func=NewsArchiveView.as_view(
        "news_archive",
        render_func=bind_render("news_archive.html"),
        err_func=ErrorHandler("sources"),
        news_archive_html="sources_news_archive.html",
    ),
)


# STATSVIEW
bp_sources.add_url_rule(
    "/stats/",
    view_func=StatsView.as_view(
        "stats",
        render_func=bind_render("sources/stats.html"),
        err_func=ErrorHandler("sources"),
        get_objects="stats",
    ),
)


# api
bp_sources.add_url_rule(
    "/api/stats/",
    view_func=StatsView.as_view(
        "api_stats",
        err_func=ErrorHandler(mode="json"),
        get_objects="stats",
    ),
)


bp_sources.add_url_rule(
    "/stats/<suite>/",
    view_func=StatsView.as_view(
        "stats_suite",
        render_func=bind_render("sources/stats_suite.html"),
        err_func=ErrorHandler("sources"),
        get_objects="stats_suite",
    ),
)


# api
bp_sources.add_url_rule(
    "/api/stats/<suite>/",
    view_func=StatsView.as_view(
        "api_stats_suite",
        render_func=jsonify,
        err_func=ErrorHandler(mode="json"),
        get_objects="stats_suite",
    ),
)


# SEARCHVIEW
bp_sources.add_url_rule(
    "/search/",
    view_func=SearchView.as_view(
        "recv_search",
        render_func=bind_render("sources/index.html"),
        err_func=ErrorHandler("sources"),
        recv_search=True,
    ),
    methods=["GET", "POST"],
)


bp_sources.add_url_rule(
    "/advancedsearch/",
    view_func=SearchView.as_view(
        "advanced_search",
        render_func=bind_render("sources/search_advanced.html"),
        err_func=ErrorHandler("sources"),
        get_objects="advanced",
    ),
)


# api
bp_sources.add_url_rule(
    "/api/advancedsearch/",
    view_func=SearchView.as_view(
        "api_advanced_search", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)


bp_sources.add_url_rule(
    "/search/<query>/",
    view_func=SearchView.as_view(
        "search",
        render_func=bind_render("search.html"),
        err_func=ErrorHandler("sources"),
        get_objects="query",
    ),
)


# api
bp_sources.add_url_rule(
    "/api/search/<query>/",
    view_func=SearchView.as_view(
        "api_search",
        render_func=jsonify,
        err_func=ErrorHandler(mode="json"),
        get_objects="query",
    ),
)


# ChecksumView
bp_sources.add_url_rule(
    "/sha256/",
    view_func=ChecksumView.as_view(
        "checksum",
        render_func=bind_render("sources/checksum.html"),
        err_func=ErrorHandler("sources"),
        pagination=True,
    ),
)


# api
bp_sources.add_url_rule(
    "/api/sha256/",
    view_func=ChecksumView.as_view(
        "api_checksum", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)


# CtagView
bp_sources.add_url_rule(
    "/ctag/",
    view_func=CtagView.as_view(
        "ctag",
        render_func=bind_render("sources/ctag.html"),
        err_func=ErrorHandler("sources"),
        pagination=True,
    ),
)


# api
bp_sources.add_url_rule(
    "/api/ctag/",
    view_func=CtagView.as_view(
        "api_ctag", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)


# PREFIXVIEW
bp_sources.add_url_rule(
    "/prefix/<prefix>/",
    view_func=PrefixView.as_view(
        "prefix",
        render_func=bind_render("prefix.html"),
        err_func=ErrorHandler("sources"),
    ),
)


# api
bp_sources.add_url_rule(
    "/api/prefix/<prefix>/",
    view_func=PrefixView.as_view(
        "api_prefix", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)


# LISTPACKAGESVIEW
bp_sources.add_url_rule(
    "/list/<int:page>/",
    view_func=ListPackagesView.as_view(
        "list_packages",
        render_func=bind_render("list.html"),
        err_func=ErrorHandler("sources"),
        pagination=True,
    ),
)


# api
bp_sources.add_url_rule(
    "/api/list/",
    view_func=ListPackagesView.as_view(
        "api_list_packages", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)

# VERSIONSVIEW
bp_sources.add_url_rule(
    "/src/<string:packagename>/",
    view_func=PackageVersionsView.as_view(
        "versions",
        render_func=bind_render("sources/source_package.html"),
        err_func=ErrorHandler("sources"),
    ),
)

# api
bp_sources.add_url_rule(
    "/api/src/<string:packagename>/",
    view_func=PackageVersionsView.as_view(
        "api_versions", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)


# SOURCEVIEW
bp_sources.add_url_rule(
    "/src/<filepath:path_to>",
    view_func=SourceView.as_view(
        "source",
        # the render func is set by the views.
        err_func=ErrorHandler("sources"),
        templatename="sources/source_file.html",
    ),
)


# api
bp_sources.add_url_rule(
    "/api/src/<filepath:path_to>/",
    view_func=SourceView.as_view(
        "api_source", err_func=ErrorHandler(mode="json"), api=True
    ),
)


# SOURCE FILE EMBEDDED ROUTING
bp_sources.add_url_rule(
    "/embed/file/<filepath:path_to>/",
    view_func=SourceView.as_view(
        "embedded_source",
        err_func=ErrorHandler("sources"),
        templatename="sources/source_file_embedded.html",
    ),
)


# INFO PER-VERSION
bp_sources.add_url_rule(
    "/info/package/<package>/<version>/",
    view_func=InfoPackageView.as_view(
        "info_package",
        render_func=bind_render("sources/infopackage.html"),
        err_func=ErrorHandler("sources"),
    ),
)


# api
bp_sources.add_url_rule(
    "/api/info/package/<package>/<version>/",
    view_func=InfoPackageView.as_view(
        "api_info_package", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)


# INFO PER-VERSION (EMBEDDED)
bp_sources.add_url_rule(
    "/embed/pkginfo/<package>/<version>/",
    view_func=InfoPackageView.as_view(
        "embedded_info_package",
        render_func=bind_render("sources/infopackage_embed.html"),
        err_func=ErrorHandler("sources"),
    ),
)
