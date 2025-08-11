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


import json
import unittest

from nose.plugins.attrib import attr

from debsources.tests.test_webapp import DebsourcesBaseWebTests


@attr("patches")
class PatchesTestCase(DebsourcesBaseWebTests, unittest.TestCase):
    def test_api_ping(self):
        rv = json.loads(self.app.get("/patches/api/ping/").data)
        self.assertEqual(rv["status"], "ok")
        self.assertEqual(rv["http_status_code"], 200)

    def test_api_packages_list(self):
        rv = json.loads(self.app.get("/patches/api/list/").data)
        self.assertIn({"name": "ocaml-curses"}, rv["packages"])
        self.assertEqual(len(rv["packages"]), 19)

    def test_api_by_prefix(self):
        rv = json.loads(self.app.get("/patches/api/prefix/o/").data)
        self.assertIn({"name": "ocaml-curses"}, rv["packages"])
        # suite specified
        rv = json.loads(self.app.get("/patches/api/prefix/o/?suite=wheezy").data)
        self.assertIn({"name": "ocaml-curses"}, rv["packages"])
        # a non-existing suite specified
        rv = json.loads(
            self.app.get("/patches/api/prefix/libc/?suite=non-existing").data
        )
        self.assertEqual([], rv["packages"])
        # special suite name "all" is specified
        rv = json.loads(self.app.get("/patches/api/prefix/libc/?suite=all").data)
        self.assertIn({"name": "libcaca"}, rv["packages"])

    def test_by_prefix(self):
        rv = self.app.get("/patches/prefix/libc/")
        self.assertIn(b"/libcaca", rv.data)
        # suite specified
        rv = self.app.get("/patches/prefix/libc/?suite=squeeze")
        self.assertIn(b"/libcaca", rv.data)
        # a non-existing suite specified
        rv = self.app.get("/patches/prefix/libc/?suite=non-existing")
        self.assertNotIn(b"/libcaca", rv.data)
        # special suite name "all" is specified
        rv = self.app.get("/patches/prefix/libc/?suite=all")
        self.assertIn(b"/libcaca", rv.data)

    def test_latest(self):
        rv = self.app.get("/patches/gnubg/latest/", follow_redirects=True)
        self.assertIn(b"Package: gnubg / 1.02.000-2", rv.data)
        rv = self.app.get(
            "/patches/beignet/latest/" "Enable-test-debug.patch/", follow_redirects=True
        )
        self.assertIn(b'<code id="sourcecode" class="diff">', rv.data)

    def test_package_summary(self):
        rv = self.app.get("/patches/beignet/1.0.0-1/")
        self.assertIn(b"Enhance debug output", rv.data)
        self.assertIn(b"utests/builtin_acos_asin.cpp</a>", rv.data)
        self.assertIn(b"8 \t5 +\t3 -\t0 !", rv.data)

        # test debian/patches/series link
        self.assertIn(
            b'<a href="/src/beignet/1.0.0-1/debian/patches/series">', rv.data
        )

        # test non quilt package
        rv = self.app.get("/patches/cvsnt/2.5.03.2382-3/")
        self.assertIn(b"The format of the patches in the package", rv.data)

    def test_view_patch(self):
        rv = self.app.get("/patches/beignet/1.0.0-1/" "Enable-test-debug.patch/")
        self.assertIn(b'<code id="sourcecode" class="diff">', rv.data)
        # highlight inside?
        self.assertIn(b"hljs.highlightBlock", rv.data)
        self.assertIn(b'highlight/highlight.min.js"></script>', rv.data)

    def test_file_deltas_links(self):
        rv = self.app.get("/patches/beignet/1.0.0-1/")
        self.assertIn(b'<a href="/src/beignet/1.0.0-1/src/cl_utils.h">', rv.data)

    def test_3_native_format(self):
        rv = self.app.get("/patches/nvidia-support/20131102+1/")
        self.assertIn(b"<td>3.0 (native)</td>", rv.data)
        self.assertIn(b"<p>This package has no patches.</p>", rv.data)
        self.assertNotIn(b"The format of the patches in the package", rv.data)

    def test_bts_link(self):
        rv = self.app.get("/patches/ledit/2.03-2/")
        self.assertIn(b'<a href="https://bugs.debian.org/672479">#672479</a>', rv.data)
        # test no bug
        rv = self.app.get("/patches/gnubg/1.02.000-2/")
        self.assertNotIn(b"Bug: ", rv.data)

    def test_extract_description(self):
        rv = self.app.get("/patches/gnubg/1.02.000-2/")
        self.assertIn(b"collected debian patches for gnubg", rv.data)
        # test long dsc
        rv = self.app.get("/patches/beignet/1.0.0-1/")
        long_dsc = (
            b"Turn on udebug so tests print their full output, and mark"
            b" failures\nby &#34;failed:&#34; instead of invisible-in-"
            b"logs colour."
        )
        self.assertIn(long_dsc, rv.data)
        # test no description header
        rv = self.app.get("/patches/unrar-nonfree/1:5.0.10-1/")
        self.assertIn(b"fix buildflags", rv.data)
        self.assertIn(b"---", rv.data)

    def test_api_patch_view(self):
        rv = json.loads(
            self.app.get(
                "/patches/api/beignet/1.0.0-1/" "Enable-test-debug.patch/"
            ).data
        )
        self.assertEqual(rv["name"], "Enable-test-debug.patch")
        self.assertEqual(rv["bug"], "")
        self.assertEqual(
            rv["url"],
            "/data/main/b/beignet/1.0.0-1/debian/" "patches/Enable-test-debug.patch",
        )
        self.assertIn("8 \t5 +\t3 -\t0 !\n utests/builtin_exp.cpp ", rv["file_deltas"])

    def test_api_summary_view(self):
        rv = json.loads(self.app.get("/patches/api/beignet/1.0.0-1/").data)
        patches = [
            "Enhance-debug-output.patch",
            "Debian-compliant-compiler-flags-handling.patch",
            "Utest-requires-deprecated-function-names.patch",
            "Link-against-terminfo.patch",
            "Enable-test-debug.patch",
        ]
        self.assertListEqual(patches, rv["patches"])
        self.assertEqual(rv["format"], "3.0 (quilt)")

    def test_pagination(self):
        base_url = "/patches/gnubg/1.02.000-2/"
        base_url_bytes = base_url.encode("utf8")
        rv = self.app.get(base_url + "?page=2")
        self.assertIn(
            b'<a href="' + base_url_bytes + b'?page=1">&laquo; Previous</a>', rv.data
        )
        rv = self.app.get(base_url + "?page=1")
        self.assertNotIn(
            b"<a href=" + base_url_bytes + b"?page=2>Next &raquo;</a>", rv.data
        )


if __name__ == "__main__":
    unittest.main(exit=False)
