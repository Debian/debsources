# Copyright (C) 2013-2021  The Debsources developers
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


import datetime
import json
import os
import unittest
from pathlib import Path

from nose.plugins.attrib import attr

from debsources.app.app_factory import AppWrapper
from debsources.tests.db_testing import DbTestFixture
from debsources.tests.testdata import TEST_DB_NAME


@attr("basewebapp")
class DebsourcesBaseWebTests(DbTestFixture):
    @classmethod
    def setUpClass(cls):
        # We use the class method here. setUpClass is called at the class
        # creation, and tearDownClass at the class destruction (instead of
        # setUp and tearDown before and after each test). This is doable here
        # because the app never modifies the db (so it's useless to
        # create/destroy it many times), and this a big gain of time.
        cls.db_setup_cls()

        app_wrapper = AppWrapper()

        # erases a few configuration parameters needed for testing:
        uri = "postgresql:///" + TEST_DB_NAME
        app_wrapper.app.config["DB_URI"] = uri
        app_wrapper.app.config["LIST_OFFSET"] = 5
        app_wrapper.app.testing = True

        app_wrapper.go()

        cls.app = app_wrapper.app.test_client()
        cls.app_wrapper = app_wrapper

    @classmethod
    def tearDownClass(cls):
        cls.app_wrapper.app.engine.dispose()
        cls.db_teardown_cls()


@attr("webapp")
class DebsourcesTestCase(DebsourcesBaseWebTests, unittest.TestCase):
    def test_app_config(self):
        # use existing config to initialize app wrapper
        config = dict(domain="test.debian.test")
        app_wrapper = AppWrapper(config=config)
        self.assertEqual(app_wrapper.app.config["domain"], "test.debian.test")

    def test_invalid_loglevel(self):
        """test with wrong supplied logging level"""
        import logging

        config = dict(LOG_LEVEL="invalid-test")
        app_wrapper = AppWrapper(config=config)
        app_wrapper.setup_logging()
        logger = app_wrapper.app.logger
        # no name, just know the index
        # the second handler is our streamhandler.
        self.assertEqual(logger.handlers[1].level, logging.INFO)

    def test_api_ping(self):
        rv = json.loads(self.app.get("/api/ping/").data)
        self.assertEqual(rv["status"], "ok")
        self.assertEqual(rv["http_status_code"], 200)

    def test_api_package_search(self):
        # test exact search result
        rv = json.loads(self.app.get("/api/search/gnubg/").data)
        self.assertEqual(rv["query"], "gnubg")
        self.assertEqual(rv["results"]["other"], [])
        self.assertEqual(rv["results"]["exact"], {"name": "gnubg"})
        # with suite specified
        rv = json.loads(self.app.get("/api/search/gnubg/?suite=squeeze").data)
        self.assertEqual(rv["query"], "gnubg")
        self.assertEqual(rv["results"]["other"], [])
        self.assertEqual(rv["results"]["exact"], {"name": "gnubg"})
        # with a non-existing suite name specified
        rv = json.loads(self.app.get("/api/search/gnubg/?suite=nonexisting").data)
        self.assertEqual(rv["query"], "gnubg")
        self.assertEqual(rv["results"]["other"], [])
        self.assertIsNone(rv["results"]["exact"])

        # other results
        rv = json.loads(self.app.get("/api/search/gnu/").data)
        self.assertEqual(rv["query"], "gnu")
        self.assertEqual(rv["results"]["other"], [{"name": "gnubg"}])
        self.assertIsNone(rv["results"]["exact"])

    def test_static_files(self):
        static_files = [
            "/static/css/base.css",
            "/static/css/debian.css",
            "/static/favicon.ico",
            "/static/bootstrap/bootstrap.min.css",
            "/static/bootstrap/bootstrap.min.js",
        ]
        for path in static_files:
            status = self.app.get(path).status_code
            self.assertEqual(status, 200)

    def test_package_search(self):
        # test exact search result
        rv = self.app.get("/search/gnubg/")
        self.assertIn(b"/src/gnubg/", rv.data)
        # with suite specified
        rv = self.app.get("/search/gnubg/?suite=squeeze")
        self.assertIn(b"/src/gnubg/", rv.data)
        # with a non-existing suite name specified
        rv = self.app.get("/search/gnubg/?suite=nonexisting")
        self.assertNotIn(b"/src/gnubg/", rv.data)
        # other results
        rv = self.app.get("/search/gnu/")
        self.assertIn(b"/src/gnubg/", rv.data)

    def test_api_case_insensitive_package_search(self):
        # exact search (lower case)
        rv = json.loads(self.app.get("/api/search/gnubg/").data)
        self.assertEqual(rv["query"], "gnubg")
        self.assertEqual(rv["results"]["exact"], {"name": "gnubg"})

        # other results (mixed case)
        rv = json.loads(self.app.get("/api/search/GnUbG/").data)
        self.assertEqual(rv["query"], "GnUbG")
        self.assertEqual(rv["results"]["other"], [{"name": "gnubg"}])

        # suite specified (mixed case)
        rv = json.loads(self.app.get("/api/search/gnubg/?suite=SQueeZe").data)
        self.assertEqual(rv["query"], "gnubg")
        self.assertEqual(rv["results"]["exact"], {"name": "gnubg"})

    def test_case_insensitive_package_search(self):
        # exact search (mixed case)
        rv = self.app.get("/search/gNuBg/")
        self.assertIn(b"/src/gnubg/", rv.data)

        # with suite specified (mixed case)
        rv = self.app.get("/search/gnubg/?suite=sQuEeZe")
        self.assertIn(b"/src/gnubg/", rv.data)

        # other results (mixed case)
        rv = self.app.get("/search/gNu/")
        self.assertIn(b"/src/gnubg/", rv.data)

    def test_static_pages(self):
        rv = self.app.get("/")
        self.assertIn(b"Debsources", rv.data)

        rv = self.app.get("/advancedsearch/")
        self.assertIn(b"Package search", rv.data)
        self.assertIn(b"File search", rv.data)
        self.assertIn(b"Code search", rv.data)

        rv = self.app.get("/doc/overview/")
        self.assertIn(b"Debsources provides Web access", rv.data)

        rv = self.app.get("/doc/api/")
        self.assertIn(b"API documentation", rv.data)

        rv = self.app.get("/doc/url/")
        self.assertIn(b"URL scheme", rv.data)

        rv = self.app.get("/doc/about/")
        self.assertIn(b"source code", rv.data)
        self.assertIn(b"is available", rv.data)

    def test_api_packages_list(self):
        rv = json.loads(self.app.get("/api/list/").data)
        self.assertIn({"name": "libcaca"}, rv["packages"])
        self.assertEqual(len(rv["packages"]), 19)

    def test_api_by_prefix(self):
        rv = json.loads(self.app.get("/api/prefix/libc/").data)
        self.assertIn({"name": "libcaca"}, rv["packages"])
        # suite specified
        rv = json.loads(self.app.get("/api/prefix/libc/?suite=squeeze").data)
        self.assertIn({"name": "libcaca"}, rv["packages"])
        # a non-existing suite specified
        rv = json.loads(self.app.get("/api/prefix/libc/?suite=non-existing").data)
        self.assertEqual([], rv["packages"])
        # special suite name "all" is specified
        rv = json.loads(self.app.get("/api/prefix/libc/?suite=all").data)
        self.assertIn({"name": "libcaca"}, rv["packages"])
        # lib* must not be in 'l'
        rv = json.loads(self.app.get("/api/prefix/l/").data)
        self.assertNotIn({"name": "libcaca"}, rv["packages"])

    def test_by_prefix(self):
        rv = self.app.get("/prefix/libc/")
        self.assertIn(b"/src/libcaca", rv.data)
        # suite specified
        rv = self.app.get("/prefix/libc/?suite=squeeze")
        self.assertIn(b"/src/libcaca", rv.data)
        # a non-existing suite specified
        rv = self.app.get("/prefix/libc/?suite=non-existing")
        self.assertNotIn(b"/src/libcaca", rv.data)
        # special suite name "all" is specified
        rv = self.app.get("/prefix/libc/?suite=all")
        self.assertIn(b"/src/libcaca", rv.data)

    def test_api_case_insensitive_prefix(self):
        rv_lower_case = json.loads(self.app.get("/api/prefix/g/").data)
        rv_upper_case = json.loads(self.app.get("/api/prefix/G/").data)
        self.assertEqual(rv_lower_case["packages"], rv_upper_case["packages"])
        # suite specified
        rv_lower_case = json.loads(self.app.get("/api/prefix/g/?suite=squeeze").data)
        rv_upper_case = json.loads(self.app.get("/api/prefix/G/?suite=SQUEEZE").data)
        self.assertEqual(rv_lower_case["packages"], rv_upper_case["packages"])

    def test_case_insensitive_prefix(self):
        rv_lower_case = self.app.get("/api/prefix/g/").data
        rv_upper_case = self.app.get("/api/prefix/G/").data
        self.assertEqual(rv_lower_case, rv_upper_case)
        # suite specified
        rv_lower_case = self.app.get("/api/prefix/g/?suite=squeeze").data
        rv_upper_case = self.app.get("/api/prefix/G/?suite=SQUEEZE").data
        self.assertEqual(rv_lower_case, rv_upper_case)

    def test_api_package(self):
        rv = json.loads(self.app.get("/api/src/ledit/").data)
        self.assertEqual(rv["path"], "ledit")
        self.assertEqual(len(rv["versions"]), 3)
        self.assertEqual(rv["type"], "package")
        # list index/order may be changed
        _v = [v for v in rv["versions"] if v["version"] == "2.01-6"][0]
        self.assertIn("squeeze", _v["suites"])
        # with suite specified
        rv = json.loads(self.app.get("/api/src/ledit/?suite=squeeze").data)
        self.assertEqual(rv["path"], "ledit")
        self.assertEqual(len(rv["versions"]), 1)
        self.assertEqual(rv["type"], "package")
        _v = [v for v in rv["versions"] if v["version"] == "2.01-6"][0]
        self.assertIn("squeeze", _v["suites"])
        # with a non-existing suite
        rv = json.loads(self.app.get("/api/src/ledit/?suite=non-existing").data)
        self.assertEqual(rv["path"], "ledit")
        self.assertEqual([], rv["versions"])
        self.assertEqual(rv["type"], "package")

    def test_package(self):
        rv = self.app.get("/src/ledit/")
        self.assertIn(b"/src/ledit/2.01-6", rv.data)
        self.assertIn(b"/src/ledit/2.03-1", rv.data)
        self.assertIn(b"/src/ledit/2.03-2", rv.data)
        self.assertIn(b"[jessie, sid]", rv.data)
        # with suite specified
        rv = self.app.get("/src/ledit/?suite=squeeze")
        self.assertIn(b"/src/ledit/2.01-6", rv.data)
        self.assertNotIn(b"/src/ledit/2.03-1", rv.data)
        self.assertNotIn(b"/src/ledit/2.03-2", rv.data)
        self.assertNotIn(b"[jessie, sid]", rv.data)
        # with a non-existing suite
        rv = self.app.get("/src/ledit/?suite=non-existing")
        self.assertNotIn(b"/src/ledit/2.01-6", rv.data)
        self.assertNotIn(b"/src/ledit/2.03-1", rv.data)
        self.assertNotIn(b"/src/ledit/2.03-2", rv.data)
        self.assertNotIn(b"[jessie, sid]", rv.data)

    def test_api_folder(self):
        rv = json.loads(self.app.get("/api/src/ledit/2.01-6/").data)
        self.assertEqual(rv["type"], "directory")
        self.assertEqual(rv["path"], "ledit/2.01-6")
        self.assertEqual(rv["package"], "ledit")
        self.assertEqual(rv["directory"], "2.01-6")
        self.assertIn(
            {
                "type": "file",
                "name": "ledit.ml",
                "percent_encoded_name": "ledit.ml",
                "hidden": False,
                "stat": {
                    "perms": "rw-r--r--",
                    "size": 45858,
                    "type": "-",
                    "symlink_dest": None,
                },
            },
            rv["content"],
        )

    def test_api_hidden_files_folder(self):
        rv = json.loads(self.app.get("/api/src/nvidia-xconfig/319.72-1/").data)
        hidden_element = {}
        shown_element = {}
        for el in rv["content"]:
            if el["name"] == ".pc":
                hidden_element = el
            elif el["name"] == "lscf.c":
                shown_element = el
        self.assertTrue(hidden_element["hidden"])
        self.assertFalse(shown_element["hidden"])

    def test_api_symlink_dest(self):
        rv = json.loads(self.app.get("/api/src/beignet/1.0.0-1/").data)
        self.assertIn(
            {
                "type": "file",
                "name": "README.md",
                "percent_encoded_name": "README.md",
                "hidden": False,
                "stat": {
                    "perms": "rwxrwxrwx",
                    "size": 17,
                    "type": "l",
                    "symlink_dest": "docs/Beignet.mdwn",
                },
            },
            rv["content"],
        )

    def test_symlink(self):
        rv = self.app.get("/src/beignet/1.0.0-1/README.md/")

        # safe symlink
        self.assertIn(b"/src/beignet/1.0.0-1/docs/Beignet.mdwn", rv.data)

        # unsafe symlinks (relatives and absolutes)

        sources_dir = self.app_wrapper.app.config["SOURCES_DIR"]
        s_relative = (
            sources_dir / "main" / "b" / "beignet" / "1.0.0-1" / "relative-link"
        )
        s_absolute = (
            sources_dir / "main" / "b" / "beignet" / "1.0.0-1" / "absolute-link"
        )
        try:
            # create symlinks
            if not os.path.lexists(s_relative):
                os.symlink(
                    "../../../../non-free/b/bsdgames-nonfree/"
                    + "2.17-3/debian/control",
                    s_relative,
                )
            if not os.path.lexists(s_absolute):
                os.symlink("/etc/passwd", s_absolute)

            # try to access them via Debsources
            rv = self.app.get("/src/beignet/1.0.0-1/relative-link/")
            self.assertEqual(403, rv.status_code)
            rv = self.app.get("/src/beignet/1.0.0-1/absolute-link/")
            self.assertEqual(403, rv.status_code)
        finally:  # clean up
            if os.path.lexists(s_relative):
                os.remove(s_relative)
            if os.path.lexists(s_absolute):
                os.remove(s_absolute)

    def test_source_file(self):
        rv = self.app.get("/src/ledit/2.01-6/ledit.ml/")

        # source code detection
        self.assertIn(b'<code id="sourcecode" class="ocaml">', rv.data)

        # highlight.js present?
        self.assertIn(b"hljs.highlightBlock", rv.data)
        self.assertIn(
            b'<script src="/static/javascript-lib/highlight/highlight.min.js">'
            b"</script>",
            rv.data,
        )

        # content of the file
        self.assertIn(b"Institut National de Recherche en Informatique", rv.data)

        # correct number of lines
        self.assertIn(b"1506 lines", rv.data)

        # stat of the file
        self.assertIn(b"stat: -rw-r--r-- 45,858 bytes", rv.data)

        # raw file link
        self.assertIn(
            b'<a id="link_download"'
            + b' href="/data/main/l/ledit/2.01-6/ledit.ml">'
            + b"download</a>",
            rv.data,
        )

        # parent folder link
        self.assertIn(
            b'<a id="link_parent_folder" href="/src/ledit/2.01-6">'
            + b"parent folder</a>",
            rv.data,
        )

    def test_source_file_text(self):
        rv = self.app.get("/src/ledit/2.01-6/README/")
        self.assertIn(b'<code id="sourcecode" class="no-highlight">', rv.data)

    def test_popup(self):
        # One popup
        rv = self.app.get(
            "src/ledit/2.01-6/go.ml/?msg=22:Cowsay:See? \
                          %20Cowsay%20variables%20are%20declared%20here."
        )
        self.assertIn(b'<pre class="messages" data-position="22">', rv.data)

        # two popups
        rv = self.app.get(
            "src/ledit/2.01-6/go.ml/?msg=22:Cowsay:See? \
                          %20Cowsay%20variables%20are%20declared%20here. \
                          &msg=10:Cowsay:See? \
                          %20Cowsay%20variables%20are%20declared%20here"
        )
        self.assertIn(b'<pre class="messages" data-position="22">', rv.data)
        self.assertIn(b'<pre class="messages" data-position="10">', rv.data)

    def test_source_file_embedded(self):
        rv = self.app.get("/embed/file/ledit/2.01-6/ledit.ml/")
        self.assertIn(b'<code id="sourcecode" class="ocaml">', rv.data)
        self.assertIn(b"Institut National de Recherche en Informatique", rv.data)
        self.assertNotIn(b'<div id="logo">', rv.data)

    def test_source_file_lang(self):
        # note we must have a trailing slash here.
        rv = self.app.get("/src/make-doc-non-dfsg/4.0-2/doc/make.info-1/")
        # redirection to the raw file.
        self.assertEqual(302, rv.status_code)
        # no redirection. no highlight
        rv = self.app.get("/src/make-doc-non-dfsg/4.0-2/doc/" "make.info-1/?lang=none")
        self.assertIn(b'<code id="sourcecode" class="no-highlight">', rv.data)
        # no redirection. highlight with cpp syntax
        rv = self.app.get("/src/make-doc-non-dfsg/4.0-2/doc/" "make.info-1/?lang=cpp")
        self.assertIn(b'<code id="sourcecode" class="cpp">', rv.data)

    def test_api_errors(self):
        rv = json.loads(self.app.get("/api/src/blablabla/").data)
        self.assertEqual(rv["error"], 404)

    def test_api_latest(self):
        rv = json.loads(
            self.app.get("/api/src/ledit/latest/", follow_redirects=True).data
        )
        self.assertIn("2.03-2", rv["path"])

    def test_suite_folder(self):
        rv = json.loads(self.app.get("/api/src/ledit/sid/", follow_redirects=True).data)
        self.assertIn("2.03-2", rv["path"])

    def test_source_file_text_suite(self):
        rv = self.app.get("/src/ledit/unstable/README/", follow_redirects=True)
        self.assertIn(b'<code id="sourcecode" class="no-highlight">', rv.data)
        rv = json.loads(
            self.app.get("/api/src/ledit/unstable/README/", follow_redirects=True).data
        )
        self.assertIn("2.03-2", rv["path"])

    def test_suite_folder_alias(self):
        rv = json.loads(
            self.app.get("/api/src/ledit/unstable/", follow_redirects=True).data
        )
        self.assertIn("2.03-2", rv["path"])

    def test_source_file_text_suite_alias(self):
        rv = self.app.get("/src/ledit/sid/README/", follow_redirects=True)
        self.assertIn(b'<code id="sourcecode" class="no-highlight">', rv.data)
        rv = json.loads(
            self.app.get("/api/src/ledit/sid/README/", follow_redirects=True).data
        )
        self.assertIn("2.03-2", rv["path"])

    def test_multiple_versions_in_suite(self):
        rv = json.loads(self.app.get("/api/src/patch/sid/", follow_redirects=True).data)
        self.assertIn("2.7.5-1", rv["path"])

    def test_multiple_versions_in_suite_alias(self):
        rv = json.loads(
            self.app.get("/api/src/patch/unstable/", follow_redirects=True).data
        )
        self.assertIn("2.7.5-1", rv["path"])

    def test_codesearch_box(self):
        rv = self.app.get("/src/ledit/2.03-2/ledit.ml/")
        self.assertIn(b'value="package:ledit "', rv.data)

    def test_pagination(self):
        rv = self.app.get("/list/2/")
        self.assertIn(b'<a href="/list/1/">&laquo; Previous</a>', rv.data)
        self.assertIn(b'<a href="/list/3/">Next &raquo;</a>', rv.data)
        self.assertIn(b"<strong>2</strong>", rv.data)

    def test_api_file_duplicates(self):
        rv = json.loads(
            self.app.get("/api/src/bsdgames-nonfree/" "2.17-3/COPYING/").data
        )
        self.assertEqual(rv["number_of_duplicates"], 3)
        self.assertEqual(
            rv["checksum"],
            ("be43f81c20961702327c10e9bd5f5a9a2b1cc" "eea850402ea562a9a76abcfa4bf"),
        )

    def test_checksum_search(self):
        rv = self.app.get(
            "/sha256/?checksum="
            "be43f81c20961702327c10e9bd5f5a9a2b1cceea850402ea562a9a76abcfa4bf"
            "&page=1"
        )
        self.assertIn(b"3 results", rv.data)
        self.assertIn(
            b"Checksum: "
            b"be43f81c20961702327c10e9bd5f5a9a2b1cceea850402ea562a9a76abcfa4bf",
            rv.data,
        )

    def test_api_checksum_search(self):
        rv = json.loads(
            self.app.get(
                "/api/sha256/?checksum=be43f81c20961702327"
                "c10e9bd5f5a9a2b1cceea850402ea562a9a76abcf"
                "a4bf&page=1"
            ).data
        )
        self.assertEqual(rv["count"], 3)
        self.assertEqual(len(rv["results"]), 3)

    def test_checksum_search_within_package(self):
        rv = self.app.get(
            "/sha256/?checksum="
            "4f721b8e5b0add185d6af7a93e577638d25eaa5c341297d95b4a27b7635b4d3f"
            "&package=susv2"
        )
        self.assertIn(b"1 result", rv.data)
        self.assertIn(
            b"Checksum: "
            b"4f721b8e5b0add185d6af7a93e577638d25eaa5c341297d95b4a27b7635b4d3f",
            rv.data,
        )

    def test_api_checksum_search_within_package(self):
        rv = json.loads(
            self.app.get(
                "/api/sha256/?checksum=4f721b8e5b0add185d6"
                "af7a93e577638d25eaa5c341297d95b4a27b7635b"
                "4d3f&package=susv2"
            ).data
        )
        self.assertEqual(rv["count"], 1)

    def test_api_search_ctag(self):
        rv = json.loads(self.app.get("/api/ctag/?ctag=name").data)
        self.assertEqual(rv["count"], 195)
        self.assertEqual(len(rv["results"]), 195)

    def test_api_search_ctag_within_package(self):
        rv = json.loads(self.app.get("/api/ctag/?ctag=name&package=ledger").data)
        self.assertEqual(rv["count"], 14)
        self.assertEqual(len(rv["results"]), 14)

    def test_api_pkg_infobox(self):
        rv = json.loads(self.app.get("/api/src/libcaca/0.99.beta17-1/").data)
        self.assertEqual(rv["pkg_infos"]["suites"], ["squeeze"])
        self.assertEqual(rv["pkg_infos"]["area"], "main")
        self.assertEqual(rv["pkg_infos"]["sloc"][0], ["ansic", 22607])
        self.assertEqual(rv["pkg_infos"]["metric"]["size"], 6584)
        p = "http://svn.debian.org/wsvn/sam-hocevar/pkg-misc/unstable/libcaca/"
        self.assertEqual(rv["pkg_infos"]["vcs_browser"], p)
        self.assertEqual(rv["pkg_infos"]["vcs_type"], "svn")
        self.assertEqual(
            rv["pkg_infos"]["pts_link"], "https://tracker.debian.org/pkg/libcaca"
        )
        self.assertEqual(rv["pkg_infos"]["ctags_count"], 3145)
        self.assertEqual(
            rv["pkg_infos"]["license"], "/copyright/license/libcaca/0.99.beta17-1/"
        )

    def test_pkg_infobox_embed(self):
        rv = self.app.get("/embed/pkginfo/libcaca/0.99.beta17-1/")
        self.assertIn(b'<div id="pkginfobox" class="pkginfobox_large">', rv.data)
        self.assertNotIn(b"<footer", rv.data)  # it's an infobox-only page

    def test_info_version(self):
        rv = self.app.get("/info/package/libcaca/0.99.beta17-1/")
        self.assertIn(b'<div id="pkginfobox" class="pkginfobox_large">', rv.data)

    def test_api_stats_suite(self):
        rv = json.loads(self.app.get("/api/stats/jessie/").data)
        self.assertEqual(rv["suite"], "jessie")
        self.assertEqual(rv["results"]["debian_jessie.ctags"], 23816)
        self.assertEqual(rv["results"]["debian_jessie.disk_usage"], 51428)
        self.assertEqual(rv["results"]["debian_jessie.source_files"], 2059)
        self.assertEqual(rv["results"]["debian_jessie.sloccount.python"], 2916)

    def test_api_released_suite(self):
        rv = json.loads(self.app.get("/api/stats/wheezy/").data)
        self.assertEqual(rv["suite"], "wheezy")
        self.assertEqual(rv["results"]["debian_wheezy.sloccount.cpp"], 37375)
        self.assertEqual(rv["results"]["debian_wheezy.source_packages"], 12)
        wheezy_rel = datetime.datetime.strptime("04052013", "%d%m%Y").date()
        self.assertEqual(rv["rel_date"], str(wheezy_rel))
        self.assertEqual(rv["rel_version"], "7")

    def test_api_stats_all(self):
        rv = json.loads(self.app.get("/api/stats/").data)
        self.assertEqual(
            sorted(rv["all_suites"]),
            [
                "debian_etch",
                "debian_experimental",
                "debian_jessie",
                "debian_sid",
                "debian_squeeze",
                "debian_wheezy",
            ],
        )
        self.assertIn("ansic", rv["languages"])
        self.assertEqual(rv["results"]["debian_sid.sloccount.ansic"], 208800)

    def test_suggestions_when_404(self):
        rv = self.app.get("/src/libcaca/0.NOPE.beta17-1/src/cacaview.c")
        self.assertIn(b"other versions of this package are available", rv.data)
        link2 = b'<a href="/src/libcaca/0.99.beta17-1/src/cacaview.c'
        self.assertIn(link2, rv.data)

    def test_bp_copyright_setup(self):
        if self.app_wrapper.app.config.get("BLUEPRINT_COPYRIGHT"):
            rv = self.app.get("/copyright/")
            self.assertEqual(200, rv.status_code)

    def test_news(self):
        # news_routes = { news_filename: associated_route }
        news_routes = {
            "sources_news.html": "/",
            "copyright_news.html": "/copyright/",
            "patches_news.html": "/patches/",
        }

        local_dir = Path(self.app_wrapper.app.config["LOCAL_DIR"])
        if not local_dir.is_dir():
            if local_dir.exists():
                # for some reason local_dir is a file, raise an IOError
                raise IOError(f"{local_dir} should be a directory.")
            else:
                local_dir.mkdir()

        # Go through each news_route and ensure it contains the data we expect
        # which is the data in local/news.html file.
        # If data doesn't exist, create dummy data to test.
        for news_file in news_routes.keys():
            fullpath = local_dir / news_file
            news_string = ""
            if fullpath.is_file():
                with open(fullpath, "r") as f:
                    news_string = f.read()
            else:
                news_string = (
                    "<ul><li>This item was created in a test for "
                    + news_file
                    + "</li></ul>"
                )
                with open(fullpath, "w") as f:
                    f.write(news_string)
            rv = self.app.get(news_routes[news_file])
            self.assertIn(news_string, rv.data.decode())

    def test_non_utf8_filename(self):
        # List folder containing a non-utf8 filename.
        rv = self.app.get("/src/aspell-is/0.51-0-4/")
        self.assertEqual(200, rv.status_code)
        self.assertIn(
            (
                b'<a href="/src/aspell-is/0.51-0-4/%25EDslenska.alias">'
                b"%EDslenska.alias</a>"
            ),
            rv.data,
        )
        # Visit that file.
        rv = self.app.get("/src/aspell-is/0.51-0-4/%25EDslenska.alias/")
        self.assertEqual(200, rv.status_code)
        self.assertIn(b"<h2>File: %EDslenska.alias</h2>", rv.data)


    def test_no_trailing_slash_for_file(self):
        """Requesting files must work with and without trailing slash."""
        rv = self.app.get("/src/libcaca/0.99.beta18-1/AUTHORS/")
        self.assertEqual(200, rv.status_code)
        rv = self.app.get("/src/libcaca/0.99.beta18-1/AUTHORS")
        self.assertEqual(200, rv.status_code)


if __name__ == "__main__":
    unittest.main(exit=False)
