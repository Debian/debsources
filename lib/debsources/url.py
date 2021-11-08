import urllib.parse


def url_encode(name: str) -> str:
    """Percent-encode a surrogate-escaped string for use in URIs.

    E.g. hello\udced -> hello%ED
    """
    return urllib.parse.quote(name, encoding="utf8", errors="surrogateescape")


def url_decode(url: str) -> str:
    """Percent-decode an URI with byte characters into a surrogate-escaped string.

    E.g. hello%ED -> hello\udced
    """
    return urllib.parse.unquote(url, encoding="utf8", errors="surrogateescape")
