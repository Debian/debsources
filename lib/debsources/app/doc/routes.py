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


from . import bp_doc

from ..helper import bind_render
from ..views import DocView, AboutView, ErrorHandler

# site errors
# XXX 500 handler cannot be registered on a blueprint
# TODO see debsources.app.view#errorhandler section
bp_doc.errorhandler(403)(lambda e: (ErrorHandler()(e, http=403), 403))
bp_doc.errorhandler(404)(lambda e: (ErrorHandler()(e, http=404), 404))


# DOCVIEW
bp_doc.add_url_rule(
    "/",
    view_func=DocView.as_view(
        "doc",
        render_func=bind_render("doc/doc.html"),
        err_func=ErrorHandler("doc"),
    ),
)


bp_doc.add_url_rule(
    "/url/",
    view_func=DocView.as_view(
        "doc_url",
        render_func=bind_render("doc/doc_url.html"),
        err_func=ErrorHandler("doc"),
    ),
)


bp_doc.add_url_rule(
    "/api/",
    view_func=DocView.as_view(
        "doc_api",
        render_func=bind_render("doc/doc_api.html"),
        err_func=ErrorHandler("doc"),
    ),
)


bp_doc.add_url_rule(
    "/overview/",
    view_func=DocView.as_view(
        "doc_overview",
        render_func=bind_render("doc/doc_overview.html"),
        err_func=ErrorHandler("doc"),
    ),
)


# ABOUTVIEW
bp_doc.add_url_rule(
    "/about/",
    view_func=AboutView.as_view(
        "about",
        render_func=bind_render("doc/about.html"),
        err_func=ErrorHandler("doc"),
    ),
)
