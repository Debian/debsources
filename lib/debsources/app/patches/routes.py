# Copyright (C) 2015-2021  The Debsources developers
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


from flask import jsonify, request, render_template

from . import bp_patches

from ..helper import bind_render, generic_before_request
from ..views import (
    IndexView,
    Ping,
    PrefixView,
    ErrorHandler,
    ListPackagesView,
    SearchView,
    NewsArchiveView,
)
from .views import SummaryView, PatchView, VersionsView
from debsources.excepts import Http404Error


# context vars
@bp_patches.context_processor
def skeleton_variables():
    site_name = bp_patches.name
    return dict(
        site_name=site_name,
    )


# 403 and 404 errors
bp_patches.errorhandler(403)(lambda e: (ErrorHandler()(e, http=403), 403))
bp_patches.errorhandler(404)(lambda e: (ErrorHandler()(e, http=404), 404))


# Before request
@bp_patches.before_request
def before_request():
    endpoints = ["summary", "api_summary", "patch_view", "api_patch_view"]
    if request.endpoint.replace("patches.", "", 1) in endpoints:
        try:
            return generic_before_request(request, 2)
        except Http404Error:
            return render_template("404.html"), 404


# INDEXVIEW
bp_patches.add_url_rule(
    "/",
    view_func=IndexView.as_view(
        "index",
        render_func=bind_render("patches/index.html"),
        err_func=ErrorHandler("patches"),
        news_html="patches_news.html",
        news_archive_html="patches_news_archive.html",
    ),
)

# NEWSARCHIVEVIEW
bp_patches.add_url_rule(
    "/news_archive",
    view_func=NewsArchiveView.as_view(
        "news_archive",
        render_func=bind_render("news_archive.html"),
        err_func=ErrorHandler("patches"),
        news_archive_html="patches_news_archive.html",
    ),
)

# ping service
bp_patches.add_url_rule(
    "/api/ping/",
    view_func=Ping.as_view(
        "ping",
    ),
)

# PREFIXVIEW
bp_patches.add_url_rule(
    "/prefix/<prefix>/",
    view_func=PrefixView.as_view(
        "prefix",
        render_func=bind_render("prefix.html"),
        err_func=ErrorHandler("patches"),
    ),
)


# api
bp_patches.add_url_rule(
    "/api/prefix/<prefix>/",
    view_func=PrefixView.as_view(
        "api_prefix", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)


# LISTPACKAGESVIEW
bp_patches.add_url_rule(
    "/list/<int:page>/",
    view_func=ListPackagesView.as_view(
        "list_packages",
        render_func=bind_render("list.html"),
        err_func=ErrorHandler("patches"),
        pagination=True,
    ),
)


# api
bp_patches.add_url_rule(
    "/api/list/",
    view_func=ListPackagesView.as_view(
        "api_list_packages", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)

# VERSIONSVIEW
bp_patches.add_url_rule(
    "/<string:packagename>/",
    view_func=VersionsView.as_view(
        "versions",
        render_func=bind_render("patches/package.html"),
        err_func=ErrorHandler("patches"),
    ),
)

# api
bp_patches.add_url_rule(
    "/api/<string:packagename>/",
    view_func=VersionsView.as_view(
        "api_patch_versions", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)

# SUMMARYVIEW
bp_patches.add_url_rule(
    "/<string:packagename>/<string:version>/",
    view_func=SummaryView.as_view(
        "summary",
        render_func=bind_render("patches/summary.html"),
        err_func=ErrorHandler("patches"),
        pagination=True,
    ),
)

# api
bp_patches.add_url_rule(
    "/api/<string:packagename>/<string:version>/",
    view_func=SummaryView.as_view(
        "api_summary", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)

# SEARCHVIEW
bp_patches.add_url_rule(
    "/search/",
    view_func=SearchView.as_view(
        "recv_search",
        render_func=bind_render("patches/index.html"),
        err_func=ErrorHandler("patches"),
        recv_search=True,
    ),
    methods=["GET", "POST"],
)


bp_patches.add_url_rule(
    "/search/<query>/",
    view_func=SearchView.as_view(
        "search",
        render_func=bind_render("search.html"),
        err_func=ErrorHandler("patches"),
        get_objects="query",
    ),
)


# api
bp_patches.add_url_rule(
    "/api/search/<query>/",
    view_func=SearchView.as_view(
        "api_search",
        render_func=jsonify,
        err_func=ErrorHandler(mode="json"),
        get_objects="query",
    ),
)

# PATCHVIEW
bp_patches.add_url_rule(
    "/<string:packagename>/<string:version>/<path:path_to>/",
    view_func=PatchView.as_view(
        "patch_view",
        render_func=bind_render("patches/patch.html"),
        err_func=ErrorHandler("patches"),
    ),
)

# api
bp_patches.add_url_rule(
    "/api/<string:packagename>/<string:version>/<path:path_to>/",
    view_func=PatchView.as_view(
        "api_patch_view", render_func=jsonify, err_func=ErrorHandler(mode="json")
    ),
)
