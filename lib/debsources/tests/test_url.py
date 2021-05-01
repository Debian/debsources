from debsources.url import url_decode, url_encode


def test_url_encode():
    assert url_encode("hello\udced") == "hello%ED"


def test_url_decode():
    assert url_decode("hello%ED") == "hello\udced"
