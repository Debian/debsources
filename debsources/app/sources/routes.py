from . import bp_sources

from .views import IndexView


bp_sources.add_url_rule(
    '/',
    view_func=IndexView.as_view(
        'index'))
