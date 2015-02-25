from . import bp_sources

from ..app.helper import bind_render
from ..app.views import DocView
from .views import IndexView


bp_sources.add_url_rule(
    '/',
    view_func=IndexView.as_view(
        'index'))


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
