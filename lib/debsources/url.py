import urllib.parse


def url_encode(name: str) -> str:
    """Percent-encode a surrogate-escaped string for use in URIs.

    E.g. hello\udced -> hello%ED
    """
    return urllib.parse.quote(bytes(name, "utf8", "surrogateescape"))


def url_decode(url: str) -> str:
    """Percent-decode an URI with byte characters into a surrogate-escaped string.

    E.g. hello%ED -> hello\udced
    """
    return urllib.parse.unquote(url, "utf8", "surrogateescape")
