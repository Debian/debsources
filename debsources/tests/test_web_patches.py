# Copyright (C) 2015  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

from __future__ import absolute_import

import json
import unittest

from nose.plugins.attrib import attr

from debsources.tests.test_webapp import DebsourcesBaseWebTests


@attr('patches')
class CopyrightTestCase(DebsourcesBaseWebTests, unittest.TestCase):

    def test_api_ping(self):
        rv = json.loads(self.app.get('/patches/api/ping/').data)
        self.assertEqual(rv["status"], "ok")
        self.assertEqual(rv["http_status_code"], 200)

    def test_api_packages_list(self):
        rv = json.loads(
            self.app.get('/patches/api/list/').data)
        self.assertIn({'name': "ocaml-curses"}, rv['packages'])
        self.assertEqual(len(rv['packages']), 18)

    def test_api_by_prefix(self):
        rv = json.loads(
            self.app.get('/patches/api/prefix/o/').data)
        self.assertIn({'name': "ocaml-curses"}, rv['packages'])
        # suite specified
        rv = json.loads(
            self.app.get('/patches/api/prefix/o/?suite=wheezy').data)
        self.assertIn({'name': "ocaml-curses"}, rv['packages'])
        # a non-existing suite specified
        rv = json.loads(self.app.get(
            '/patches/api/prefix/libc/?suite=non-existing').data)
        self.assertEqual([], rv['packages'])
        # special suite name "all" is specified
        rv = json.loads(
            self.app.get('/patches/api/prefix/libc/?suite=all').data)
        self.assertIn({'name': "libcaca"}, rv['packages'])

    def test_by_prefix(self):
        rv = self.app.get('/patches/prefix/libc/')
        self.assertIn("/summary/libcaca", rv.data)
        # suite specified
        rv = self.app.get('/patches/prefix/libc/?suite=squeeze')
        self.assertIn("/summary/libcaca", rv.data)
        # a non-existing suite specified
        rv = self.app.get(
            '/patches/prefix/libc/?suite=non-existing')
        self.assertNotIn("/summary/libcaca", rv.data)
        # special suite name "all" is specified
        rv = self.app.get(
            '/patches/prefix/libc/?suite=all')
        self.assertIn("/summary/libcaca", rv.data)

    def test_latest(self):
        rv = self.app.get('/patches/summary/gnubg/latest/',
                          follow_redirects=True)
        self.assertIn("Package: gnubg / 1.02.000-2", rv.data)

    def test_package_summary(self):
        rv = self.app.get('/patches/summary/beignet/1.0.0-1/')
        self.assertIn("Enhance debug output", rv.data)
        self.assertIn("utests/builtin_acos_asin.cpp</a> |    8 +++++---",
                      rv.data)

        # test non quilt package
        rv = self.app.get('/patches/summary/cvsnt/2.5.03.2382-3/')
        self.assertIn("The format of the patches in the package", rv.data)

    def test_view_patch(self):
        rv = self.app.get('/patches/patch/beignet/1.0.0-1/'
                          'Enable-test-debug.patch/')
        self.assertIn('<code id="sourcecode" class="diff">', rv.data)
        # highlight inside?
        self.assertIn('hljs.highlightBlock', rv.data)
        self.assertIn('highlight/highlight.min.js"></script>', rv.data)

    def test_file_deltas_links(self):
        rv = self.app.get('/patches/summary/beignet/1.0.0-1/')
        self.assertIn('<a href="/src/beignet/1.0.0-1/src/cl_utils.h/">',
                      rv.data)

    def test_summary_404(self):
        rv = self.app.get("/patches/summary/gnubg/1.02.000-2/foo",
                          follow_redirects=True)
        self.assertIn('other versions of this package are available', rv.data)
        link = '<a href="/patches/summary/gnubg/0.90+20091206-4/">'
        self.assertIn(link, rv.data)

    def test_3_native_format(self):
        rv = self.app.get("/patches/summary/nvidia-support/20131102+1/")
        self.assertIn('<td>3.0 (native)</td>', rv.data)
        self.assertIn('<p>This package has no patches.</p>', rv.data)
        self.assertNotIn('The format of the patches in the package', rv.data)

    def test_bts_link(self):
        rv = self.app.get('/patches/summary/ledit/2.03-2/')
        self.assertIn('<a href="https://bugs.debian.org/672479">#672479</a>',
                      rv.data)
        # test no bug
        rv = self.app.get('/patches/patch/gnubg/1.02.000-2/')
        self.assertNotIn('Bug: ', rv.data)

    def test_extract_description(self):
        rv = self.app.get('/patches/summary/gnubg/1.02.000-2/')
        self.assertIn('collected debian patches for gnubg', rv.data)
        # test long dsc
        rv = self.app.get('/patches/summary/beignet/1.0.0-1/')
        long_dsc = 'Turn on udebug so tests print their full output, and mark' \
                   ' failures\nby &#34;failed:&#34; instead of invisible-in-' \
                   'logs colour.'
        self.assertIn(long_dsc, rv.data)
        # test no description header
        rv = self.app.get('/patches/summary/unrar-nonfree/1:5.0.10-1/')
        self.assertIn('fix buildflags', rv.data)
        self.assertIn('---', rv.data)


if __name__ == '__main__':
    unittest.main(exit=False)
