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

    def test_checksum_api(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=be43f81c20961702327'
            'c10e9bd5f5a9a2b1cceea850402ea562a9a76abcf'
            'a4bf').data)

        # verify number of files in d/copyright
        self.assertEqual(rv['count'], len(rv['copyright']))

        self.assertEqual(rv['copyright'][0]['license'], None)
        self.assertEqual(rv['copyright'][1]['license'],
                         'BSD')
        self.assertEqual(rv['copyright'][2]['package'],
                         'bsdgames-nonfree')
        self.assertEqual(rv['copyright'][2]['version'],
                         '2.17-6')
        self.assertEqual(rv['copyright'][2]['path'],
                         'COPYING')

        # verify folder/* /* functionnality
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a706b4cfa9661a6b8a').data)

        self.assertEqual(rv['count'], 12)
        # debian/* under gpl2
        self.assertEqual(rv['copyright'][6]['license'],
                         'GPL-2+')
        # /* under gpl2
        self.assertEqual(rv['copyright'][8]['license'],
                         'GPL-2+')

        # need test for /f1/f2/filename where f1/* under l1 and f2/* under l2

    def test_package_filter_checksum(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a70'
            '6b4cfa9661a6b8a&package=gnubg').data)
        self.assertEqual(rv['count'], 2)
        self.assertEqual(rv['copyright'][0]['package'],
                         'gnubg')
        self.assertNotEqual(rv['copyright'][0]['version'],
                            rv['copyright'][1]['version'])

    def test_suite_filter_checksum(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/'
            '?checksum=2e6d31a5983a91251bfae5'
            'aefa1c0a19d8ba3cf601d0e8a70'
            '6b4cfa9661a6b8a&suite=etch').data)
        self.assertEqual(rv['count'], 0)
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
        self.assertGreaterEqual(rv2['count'], rv['count'])


if __name__ == '__main__':
    unittest.main(exit=False)
