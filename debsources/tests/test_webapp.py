# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import json

from nose.plugins.attrib import attr

from debsources.tests.db_testing import DbTestFixture
from debsources.tests.testdata import TEST_DB_NAME
from debsources.app.app_factory import AppWrapper


@attr('webapp')
class DebsourcesTestCase(unittest.TestCase, DbTestFixture):
    @classmethod
    def setUpClass(cls):
        """
        We use the class method here. setUpClass is called at the class
        creation, and tearDownClass at the class destruction (instead of
        setUp and tearDown before and after each test). This is doable
        here because the app never modifies the db (so it's useless to
        create/destroy it many times), and this a big gain of time.
        """
        cls.db_setup_cls()

        # creates an app object, which is used to run queries
        from debsources.app import app_wrapper

        # erases a few configuration parameters needed for testing:
        uri = "postgresql:///" + TEST_DB_NAME
        app_wrapper.app.config["SQLALCHEMY_DATABASE_URI"] = uri
        app_wrapper.app.config['LIST_OFFSET'] = 5

        app_wrapper.go()

        cls.app = app_wrapper.app.test_client()
        cls.app_wrapper = app_wrapper

    @classmethod
    def tearDownClass(cls):
        cls.app_wrapper.engine.dispose()
        cls.db_teardown_cls()

    def test_app_config(self):
        """use existing config to initialize app wrapper"""
        config = dict(domain="test.debian.test")
        app_wrapper = AppWrapper(config=config)
        self.assertEqual(app_wrapper.app.config["domain"],
                         "test.debian.test")

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

    def test_ping(self):
        rv = json.loads(self.app.get('/api/ping/').data)
        self.assertEqual(rv["status"], "ok")
        self.assertEqual(rv["http_status_code"], 200)

    def test_package_search(self):
        # exact search
        rv = json.loads(self.app.get('/api/search/gnubg/').data)
        self.assertEqual(rv['query'], 'gnubg')
        self.assertEqual(rv['results']['other'], [])
        self.assertEqual(rv['results']['exact'], {'name': "gnubg"})

        # other results
        rv = json.loads(self.app.get('/api/search/gnu/').data)
        self.assertEqual(rv['query'], 'gnu')
        self.assertEqual(rv['results']['other'], [{'name': "gnubg"}])
        self.assertIsNone(rv['results']['exact'])

    def test_case_insensitive_package_search(self):
        # exact search (lower case)
        rv = json.loads(self.app.get('/api/search/gnubg/').data)
        self.assertEqual(rv['query'], 'gnubg')
        self.assertEqual(rv['results']['exact'], {'name': "gnubg"})

        # other results (mixed case)
        rv = json.loads(self.app.get('/api/search/GnUbG/').data)
        self.assertEqual(rv['query'], 'GnUbG')
        self.assertEqual(rv['results']['other'], [{'name': "gnubg"}])

    def test_static_pages(self):
        rv = self.app.get('/')
        self.assertIn('Debsources', rv.data)

        rv = self.app.get('/advancedsearch/')
        self.assertIn('Package search', rv.data)
        self.assertIn('File search', rv.data)
        self.assertIn('Code search', rv.data)

        rv = self.app.get('/doc/overview/')
        self.assertIn('Debsources provides Web access', rv.data)

        rv = self.app.get('/doc/api/')
        self.assertIn('API documentation', rv.data)

        rv = self.app.get('/doc/url/')
        self.assertIn('URL scheme', rv.data)

        rv = self.app.get('/about/')
        self.assertIn('source code', rv.data)
        self.assertIn('is available', rv.data)

    def test_packages_list(self):
        rv = json.loads(self.app.get('/api/list/').data)
        self.assertIn({'name': "libcaca"}, rv['packages'])
        self.assertEqual(len(rv['packages']), 14)

    def test_by_prefix(self):
        rv = json.loads(self.app.get('/api/prefix/libc/').data)
        self.assertIn({'name': "libcaca"}, rv['packages'])

    def test_case_insensitive_prefix(self):
        rv_lower_case = json.loads(self.app.get('/api/prefix/g/').data)
        rv_upper_case = json.loads(self.app.get('/api/prefix/G/').data)
        self.assertEqual(rv_lower_case['packages'], rv_upper_case['packages'])

    def test_package(self):
        rv = json.loads(self.app.get('/api/src/ledit/').data)
        self.assertEqual(rv['path'], "ledit")
        self.assertEqual(len(rv['versions']), 3)
        self.assertEqual(rv['type'], "package")
        # list index/order may be changed
        _v = [_v for _v in rv['versions'] if _v['version'] == '2.01-6'][0]
        self.assertIn('squeeze', _v['suites'])

    def test_folder(self):
        rv = json.loads(self.app.get('/api/src/ledit/2.01-6/').data)
        self.assertEqual(rv['type'], "directory")
        self.assertEqual(rv['path'], "ledit/2.01-6")
        self.assertEqual(rv['package'], "ledit")
        self.assertEqual(rv['directory'], "2.01-6")
        self.assertIn({"type": "file",
                       "name": "ledit.ml",
                       "stat": {"perms": "rw-r--r--",
                                "size": 45858,
                                "type": "-"}
                       }, rv['content'])

    def test_source_file(self):
        rv = self.app.get('/src/ledit/2.01-6/ledit.ml/')

        # source code detection
        self.assertIn('<code id="sourcecode" class="ocaml">', rv.data)

        # highlight.js present?
        self.assertIn('hljs.highlightBlock', rv.data)
        self.assertIn('<script src="/javascript/highlight/highlight.min.js">'
                      '</script>', rv.data)

        # content of the file
        self.assertIn('Institut National de Recherche en Informatique',
                      rv.data)

        # correct number of lines
        self.assertIn('1506 lines', rv.data)

        # stat of the file
        self.assertIn('stat: -rw-r--r-- 45,858 bytes', rv.data)

        # raw file link
        self.assertIn('<a href="/data/main/l/ledit/2.01-6/ledit.ml">'
                      'download</a>', rv.data)

        # parent folder link
        self.assertIn('<a href="/src/ledit/2.01-6/">parent folder</a>',
                      rv.data)

    def test_source_file_text(self):
        rv = self.app.get('/src/ledit/2.01-6/README/')
        self.assertIn('<code id="sourcecode" class="no-highlight">', rv.data)

    def test_source_file_embedded(self):
        rv = self.app.get('/embed/file/ledit/2.01-6/ledit.ml/')
        self.assertIn('<code id="sourcecode" class="ocaml">', rv.data)
        self.assertIn('Institut National de Recherche en Informatique',
                      rv.data)
        self.assertNotIn('<div id="logo">', rv.data)

    def test_errors(self):
        rv = json.loads(self.app.get('/api/src/blablabla/').data)
        self.assertEqual(rv['error'], 404)

    def test_latest(self):
        rv = json.loads(self.app.get('/api/src/ledit/latest/',
                                     follow_redirects=True).data)
        self.assertIn("2.03-2", rv['path'])

    def test_codesearch_box(self):
        rv = self.app.get('/src/ledit/2.03-2/ledit.ml/')
        self.assertIn('value="package:ledit "', rv.data)

    def test_pagination(self):
        rv = self.app.get('/list/2/')
        self.assertIn('<a href="/list/1/">&laquo; Previous</a>', rv.data)
        self.assertIn('<a href="/list/3/">Next &raquo;</a>', rv.data)
        self.assertIn('<strong>2</strong>', rv.data)

    def test_file_duplicates(self):
        rv = json.loads(self.app.get('/api/src/bsdgames-nonfree/'
                                     '2.17-3/COPYING/').data)
        self.assertEqual(rv["number_of_duplicates"], 3)
        self.assertEqual(rv["checksum"],
                         ("be43f81c20961702327c10e9bd5f5a9a2b1cc"
                          "eea850402ea562a9a76abcfa4bf"))

    def test_checksum_search(self):
        rv = json.loads(self.app.get(
            '/api/sha256/?checksum=be43f81c20961702327'
            'c10e9bd5f5a9a2b1cceea850402ea562a9a76abcf'
            'a4bf&page=1').data)
        self.assertEqual(rv["count"], 3)
        self.assertEqual(len(rv["results"]), 3)

    def test_checksum_search_within_package(self):
        rv = json.loads(self.app.get(
            '/api/sha256/?checksum=4f721b8e5b0add185d6'
            'af7a93e577638d25eaa5c341297d95b4a27b7635b'
            '4d3f&package=susv2').data)
        self.assertEqual(rv["count"], 1)

    def test_search_ctag(self):
        rv = json.loads(self.app.get('/api/ctag/?ctag=name').data)
        self.assertEqual(rv["count"], 88)
        self.assertEqual(len(rv["results"]), 88)

    def test_search_ctag_within_package(self):
        rv = json.loads(self.app.get(
            '/api/ctag/?ctag=name&package=ledger').data)
        self.assertEqual(rv["count"], 14)
        self.assertEqual(len(rv["results"]), 14)

    def test_pkg_infobox(self):
        rv = json.loads(self.app.get('/api/src/libcaca/0.99.beta17-1/').data)
        self.assertEqual(rv["pkg_infos"]["suites"], ["squeeze"])
        self.assertEqual(rv["pkg_infos"]["area"], "main")
        self.assertEqual(rv["pkg_infos"]["sloc"][0], ["ansic", 22607])
        self.assertEqual(rv["pkg_infos"]["metric"]["size"], 6584)
        p = "http://svn.debian.org/wsvn/sam-hocevar/pkg-misc/unstable/libcaca/"
        self.assertEqual(rv["pkg_infos"]["vcs_browser"], p)
        self.assertEqual(rv["pkg_infos"]["vcs_type"], "svn")
        self.assertEqual(rv["pkg_infos"]["pts_link"],
                         "http://tracker.debian.org/pkg/libcaca")
        self.assertEqual(rv["pkg_infos"]["ctags_count"], 3145)

    def test_pkg_infobox_embed(self):
        rv = self.app.get('/embed/pkginfo/libcaca/0.99.beta17-1/')
        self.assertIn('<div id="pkginfobox" class="pkginfobox_large">',
                      rv.data)
        self.assertNotIn('<footer', rv.data)  # it's an infobox-only page

    def test_info_version(self):
        rv = self.app.get('/info/package/libcaca/0.99.beta17-1/')
        self.assertIn('<div id="pkginfobox" class="pkginfobox_large">',
                      rv.data)

    def test_stats_suite(self):
        rv = json.loads(self.app.get('/api/stats/jessie/').data)
        self.assertEqual(rv["suite"], "jessie")
        # self.assertEqual(rv["results"]["debian_jessie.ctags"], 21767)
        # self.assertEqual(rv["results"]["debian_jessie.disk_usage"], 43032)
        self.assertEqual(rv["results"]["debian_jessie.source_files"], 1677)
        self.assertEqual(rv["results"]["debian_jessie.sloccount.python"], 2916)

    def test_stats_all(self):
        rv = json.loads(self.app.get('/api/stats/').data)
        self.assertEqual(sorted(rv["all_suites"]),
                         ["debian_experimental", "debian_jessie", "debian_sid",
                          "debian_squeeze", "debian_wheezy"])
        self.assertIn("ansic", rv["languages"])
        self.assertEqual(rv["results"]["debian_sid.sloccount.ansic"], 140353)

    def test_suggestions_when_404(self):
        rv = self.app.get('/src/libcaca/0.NOPE.beta17-1/src/cacaview.c/')
        self.assertIn('other versions of this package are available', rv.data)
        link2 = '<a href="/src/libcaca/0.99.beta17-1/src/cacaview.c/">'
        self.assertIn(link2, rv.data)

if __name__ == '__main__':
    unittest.main(exit=False)
