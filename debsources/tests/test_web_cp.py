# Copyright (C) 2013-2015  The Debsources developers <info@sources.debian.net>.
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


@attr('copyright')
class CopyrightTestCase(DebsourcesBaseWebTests, unittest.TestCase):

    def test_api_ping(self):
        rv = json.loads(self.app.get('/copyright/api/ping/').data)
        self.assertEqual(rv["status"], "ok")
        self.assertEqual(rv["http_status_code"], 200)

    def test_api_packages_list(self):
        rv = json.loads(
            self.app.get('/copyright/api/list/').data)
        self.assertIn({'name': "ocaml-curses"}, rv['packages'])
        self.assertEqual(len(rv['packages']), 18)

    def test_api_by_prefix(self):
        rv = json.loads(
            self.app.get('/copyright/api/prefix/o/').data)
        self.assertIn({'name': "ocaml-curses"}, rv['packages'])
        # suite specified
        rv = json.loads(
            self.app.get('/copyright/api/prefix/o/?suite=wheezy').data)
        self.assertIn({'name': "ocaml-curses"}, rv['packages'])
        # a non-existing suite specified
        rv = json.loads(self.app.get(
            '/copyright/api/prefix/libc/?suite=non-existing').data)
        self.assertEqual([], rv['packages'])
        # special suite name "all" is specified
        rv = json.loads(
            self.app.get('/copyright/api/prefix/libc/?suite=all').data)
        self.assertIn({'name': "libcaca"}, rv['packages'])

    def test_by_prefix(self):
        rv = self.app.get('/copyright/prefix/libc/')
        self.assertIn("/license/libcaca", rv.data)
        # suite specified
        rv = self.app.get('/copyright/prefix/libc/?suite=squeeze')
        self.assertIn("/license/libcaca", rv.data)
        # a non-existing suite specified
        rv = self.app.get(
            '/copyright/prefix/libc/?suite=non-existing')
        self.assertNotIn("/license/libcaca", rv.data)
        # special suite name "all" is specified
        rv = self.app.get(
            '/copyright/prefix/libc/?suite=all')
        self.assertIn("/license/libcaca", rv.data)

    def test_latest(self):
        rv = self.app.get('/copyright/license/gnubg/latest/',
                          follow_redirects=True)
        self.assertIn("Package: gnubg / 1.02.000-2", rv.data)

    def test_non_machine_readable_license(self):
        rv = self.app.get('/copyright/license/gnubg/0.90+20091206-4/')
        self.assertNotIn("<p class=\'r_glob\'>", rv.data)

    def test_machine_readable_license(self):
        rv = self.app.get('/copyright/license/gnubg/1.02.000-2/')
        self.assertIn("<p class=\'r_glob\'>", rv.data)

    def test_common_licenses_link(self):
        rv = self.app.get('/copyright/license/gnubg/1.02.000-2/')
        self.assertIn("http://sources.debian.net/src/base-files/"
                      "latest/licenses/GFDL-1.3", rv.data)

    def test_api_checksum(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=be43f81c20961702327'
            'c10e9bd5f5a9a2b1cceea850402ea562a9a76abcf'
            'a4bf').data)

        self.assertEqual(rv['result']['copyright'][0]['license'], None)
        self.assertEqual(rv['result']['copyright'][1]['license'],
                         'BSD')
        self.assertEqual(rv['result']['copyright'][2]['package'],
                         'bsdgames-nonfree')
        self.assertEqual(rv['result']['copyright'][2]['version'],
                         '2.17-6')
        self.assertEqual(rv['result']['copyright'][2]['path'],
                         'COPYING')

        # verify folder/* /* functionnality
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a706b4cfa9661a6b8a').data)

        # debian/* under gpl2
        self.assertEqual(rv['result']['copyright'][6]['license'],
                         'GPL-2+')
        # /* under gpl2
        self.assertEqual(rv['result']['copyright'][8]['license'],
                         'GPL-2+')

        # test non existing checksum
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a71a6b8a').data)
        self.assertEqual(rv['return_code'], 404)

    def test_api_package_filter_checksum(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a70'
            '6b4cfa9661a6b8a&package=gnubg').data)
        self.assertEqual(rv['result']['copyright'][0]['package'],
                         'gnubg')
        self.assertNotEqual(rv['result']['copyright'][0]['version'],
                            rv['result']['copyright'][1]['version'])

    def test_api_suite_filter_checksum(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a70'
            '6b4cfa9661a6b8a&suite=jessie').data)
        rv2 = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a70'
            '6b4cfa9661a6b8a').data)
        self.assertGreaterEqual(len(rv2['result']['copyright']),
                                len(rv['result']['copyright']))

    def test_api_checksum_latest(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a70'
            '6b4cfa9661a6b8a&suite=latest').data)
        rv2 = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a70'
            '6b4cfa9661a6b8a').data)
        self.assertLessEqual(len(rv['result']['copyright']),
                             len(rv2['result']['copyright']))

    def test_checksum_view(self):
        rv = self.app.get("/copyright/sha256/?checksum="
                          "2e6d31a5983a91251bfae5aefa1c0a"
                          "19d8ba3cf601d0e8a706b4cfa9661a6b8a")
        self.assertIn("This checksum appears 12 times", rv.data)
        self.assertIn("Most frequent license is: <i>GPL-2+</i>", rv.data)

    def test_checksum_view_package_filter(self):
        rv = self.app.get("/copyright/sha256/?checksum="
                          "2e6d31a5983a91251bfae5aefa1c0a"
                          "19d8ba3cf601d0e8a706b4cfa9661a6b8a&package=gnubg")
        self.assertIn("This checksum appears 2 times", rv.data)
        self.assertNotIn("Most common package", rv.data)

    def test_checksum_view_suite_filter(self):
        rv = self.app.get("/copyright/sha256/?checksum="
                          "2e6d31a5983a91251bfae5aefa1c0a"
                          "19d8ba3cf601d0e8a706b4cfa9661a6b8a&suite=latest")
        self.assertIn("This checksum appears 8 times", rv.data)
        rv = self.app.get("/copyright/sha256/?checksum="
                          "2e6d31a5983a91251bfae5aefa1c0a"
                          "19d8ba3cf601d0e8a706b4cfa9661a6b8a&suite=jessie")
        self.assertIn("This checksum appears 7 times", rv.data)

    def test_checksum_view_one_result(self):
        rv = self.app.get("/copyright/sha256/?checksum="
                          "2e6d31a5983a91251bfae5aefa1c0a"
                          "19d8ba3cf601d0e8a706b4cfa9661a6b8a&package=beignet")
        self.assertIn("This checksum appears 1 time", rv.data)
        self.assertNotIn("<h3>Details</h3>", rv.data)

    def test_checksum_404(self):
        rv = self.app.get("/copyright/sha256/?checksum="
                          "2e6d31a5983a91251bfae5aefa1c0a19d8"
                          "ba3cf60d0e8a706b4cfa9661a6b8a")
        self.assertIn("0 results", rv.data)

    def test_api_search_filename_package(self):
        # test package requirement
        '''rv = json.loads(self.app.get(
            "/copyright/api/file/random/debian/copyright/").data)
        self.assertEqual(rv['error'], 'File not found')
        self.assertEqual(rv['return_code'], 404)'''

        rv = json.loads(self.app.get(
            "/copyright/api/file/gnubg/1.02.000-2/Makefile.am/").data)
        self.assertEqual(len(rv['result']), 1)
        self.assertEqual(rv['result'][0]['copyright']['path'], 'Makefile.am')
        self.assertEqual(rv['result'][0]['copyright']['license'], 'GPL-3+')

        # test with folder
        rv = json.loads(self.app.get(
            "/copyright/api/file/gnubg/0.90+20120429-1/"
            "doc/gnubg/gnubg.html/").data)
        self.assertEqual(rv['result'][0]['copyright']['license'], None)

    def test_api_search_filename_suite_filter(self):
        rv = json.loads(self.app.get(
            "/copyright/api/file/gnubg/wheezy/doc/gnubg/gnubg.html/",
            follow_redirects=True).data)
        self.assertEqual(rv['result'][0]['copyright']['version'],
                         '0.90+20120429-1')
        rv = json.loads(self.app.get(
            "/copyright/api/file/gnubg/squeeze/doc/gnubg/gnubg.html/",
            follow_redirects=True).data)
        self.assertEqual(rv['result'][0]['copyright']['version'],
                         '0.90+20091206-4')

    def test_api_search_filename_latest(self):
        rv = json.loads(self.app.get(
            "/copyright/api/file/gnubg/latest/doc/gnubg/gnubg.html/",
            follow_redirects=True).data)
        self.assertEqual(rv['result'][0]['copyright']['version'],
                         '1.02.000-2')

    def test_api_search_filename_all(self):
        rv = json.loads(self.app.get(
            "/copyright/api/file/gnubg/all/doc/gnubg/gnubg.html/").data)
        self.assertEqual(len(rv['result']), 3)

    def test_batch_api(self):
        data = {"checksums": ["2e6d31a5983a91251bfae5aefa1c0a19d8ba3cf601d0e"
                              "8a706b4cfa9661a6b8a",
                              "4f721b8e5b0add185d6af7a93e577638d25eaa5c34129"
                              "7d95b4a27b7635b4d3f",
                              "sha_does_not_exist"]
                }
        rv = json.loads(self.app.post("/copyright/api/sha256/",
                                      data=data).data)
        self.assertEqual("2e6d31a5983a91251bfae5aefa1c0a19d8ba3cf601d0e"
                         "8a706b4cfa9661a6b8a", rv['result'][0]['checksum'])
        self.assertEqual(len(rv['result'][0]['copyright']), 12)
        self.assertEqual(rv['result'][2]['count'], 0)

    def test_batch_api_package_filter(self):
        data = {"checksums": ["2e6d31a5983a91251bfae5aefa1c0a19d8ba3cf601d0e"
                              "8a706b4cfa9661a6b8a",
                              "4f721b8e5b0add185d6af7a93e577638d25eaa5c34129"
                              "7d95b4a27b7635b4d3f"],
                "package": 'gnubg'
                }
        rv = json.loads(self.app.post("/copyright/api/sha256/",
                                      data=data).data)
        self.assertEqual("2e6d31a5983a91251bfae5aefa1c0a19d8ba3cf601d0e"
                         "8a706b4cfa9661a6b8a", rv['result'][0]['checksum'])
        self.assertEqual(len(rv['result'][0]['copyright']), 2)
        self.assertEqual(rv['result'][1]['count'], 0)

    def test_batch_api_suite_filter(self):
        data = {"checksums": ["2e6d31a5983a91251bfae5aefa1c0a19d8ba3cf601d0e"
                              "8a706b4cfa9661a6b8a",
                              "4f721b8e5b0add185d6af7a93e577638d25eaa5c34129"
                              "7d95b4a27b7635b4d3f"],
                "suite": 'jessie'
                }
        rv = json.loads(self.app.post("/copyright/api/sha256/",
                                      data=data).data)
        self.assertEqual("2e6d31a5983a91251bfae5aefa1c0a19d8ba3cf601d0e"
                         "8a706b4cfa9661a6b8a", rv['result'][0]['checksum'])
        self.assertEqual(len(rv['result'][0]['copyright']), 7)
        self.assertEqual(len(rv['result'][1]['copyright']), 2)

    def test_batch_api_latest_suite(self):
        data = {"checksums": ["2e6d31a5983a91251bfae5aefa1c0a19d8ba3cf601d0e"
                              "8a706b4cfa9661a6b8a",
                              "4f721b8e5b0add185d6af7a93e577638d25eaa5c34129"
                              "7d95b4a27b7635b4d3f"],
                "suite": 'latest'
                }
        rv = json.loads(self.app.post("/copyright/api/sha256/",
                                      data=data).data)
        self.assertEqual(len(rv['result'][0]['copyright']), 8)
        self.assertEqual(len(rv['result'][1]['copyright']), 2)

    def test_search_filename_all(self):
        rv = self.app.get(
            "/copyright/file/gnubg/all/doc/gnubg/gnubg.html/").data
        self.assertIn("File name appears 3", rv)

    def test_search_filename_suite_non_existing(self):
        rv = self.app.get(
            "/copyright/file/gnubg/not/doc/gnubg/gnubg.html/").data
        self.assertIn("not found", rv)

    def test_search_filename_suite_filter(self):
        rv = self.app.get("/copyright/file/gnubg/jessie/doc/gnubg/gnubg.html/",
                          follow_redirects=True)
        self.assertNotIn("File name appears", rv.data)

    def test_search_filename(self):
        rv = self.app.get("/copyright/file/gnubg/1.02.000-2"
                          "/doc/gnubg/gnubg.html/", follow_redirects=True)
        self.assertIn("GPL-3+", rv.data)

    def test_synopsis_parsing(self):
        rv = self.app.get("/copyright/license/gnubg/1.02.000-2/")
        self.assertIn("<a href=\"#license-0\">FSF-configure</a>", rv.data)
        # Test separating by ',' and, or and create correct links
        synopsis = "<a href=\"#license-0\">FSF-configure</a>, and  " \
                   "<a href=\"http://opensource.org/licenses/GPL-2.0\">GPL-2+" \
                   " with Libtool exception</a> or  <a href=\"http://opensou" \
                   "rce.org/licenses/GPL-3.0\">GPL-3+</a>"
        self.assertIn(synopsis, rv.data)


if __name__ == '__main__':
    unittest.main(exit=False)
