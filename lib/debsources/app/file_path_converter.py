"""Custom variable type to be used in URLs containing a path to a file.

To represent a path in the content of web pages, percent encoding is
used.  This allows to keep most of the path human-readable, and only
characters outside of those allowed in an URL are displayed under the
form %XY.

To create an URL from a file path, double-percent encoding is used.
This is because URLs are percent-decoded by gateways before passing
down the result to the application through WSGI.  Using double-percent
encoding allows to be safe, and avoids the gateway to drop bytes that
can't be decoded to ASCII or UTF-8.

For example, a file b"hello\xed" can't be decoded to UTF-8.

It will be represented as "hello%ED" in web pages.

It will be represented as "hello%25%ED" in an URL.  When the gateway
receives such an URL, it decodes it to "hello%ED" and passes down this
value through WSGI.  It is then decoded to an utf-8 surrogate-escaped
string, used to create a correct `filepath.Path` object.
"""

import urllib.parse

from werkzeug.routing import PathConverter

from debsources.url import url_decode, url_encode


class FilePathConverter(PathConverter):
    """Convert utf-8 surrogate-escaped strings to URLs and back.

    A Werkzeug converter allows to define custom variable types when
    defining URL routes.
    """

    def to_python(self, value):
        """Decode URL to utf-8 surrogate-escaped string."""
        return url_decode(value)

    def to_url(self, value):
        """Encode utf-8 surrogate-escaped string to URL.

        Since URLs are decoded twice, once by the WSGI gateway, and
        once by the Python application, producing such URLs needs a
        double-percent encoding. See module documentation.
        """
        return urllib.parse.quote(url_encode(value))
