from __future__ import absolute_import

from flask.views import View


# this is just a placeholder
class IndexView(View):

    def dispatch_request(self):
        return "Hello World"
