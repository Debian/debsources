from . import bp_copyright

from .views import IndexView


bp_copyright.add_url_rule(
    '/',
    view_func=IndexView.as_view(
        'index'))
