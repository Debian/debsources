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


import os
import sys
import unittest
import tempfile
import json

from nose.tools import istest, nottest
from nose.plugins.attrib import attr

from debsources.tests.db_testing import DbTestFixture
from debsources.tests.testdata import TEST_DB_NAME

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
    
    def test_ping(self):
        rv = json.loads(self.app.get('/api/ping/').data)
        assert rv["status"] == "ok"
        assert rv["http_status_code"] == 200
    
    def test_package_search(self):
        # exact search
        rv = json.loads(self.app.get('/api/search/gnubg/').data)
        assert rv['query'] == 'gnubg'
        assert rv['results']['other'] == []
        assert rv['results']['exact'] == {'name': "gnubg"}
        
        # other results
        rv = json.loads(self.app.get('/api/search/gnu/').data)
        assert rv['query'] == 'gnu'
        assert rv['results']['other'] == [{'name': "gnubg"}]
        assert rv['results']['exact'] is None
    
    def test_static_pages(self):
        rv = self.app.get('/')
        assert 'Debsources' in rv.data
        
        rv = self.app.get('/advancedsearch/')
        assert 'Package search' in rv.data
        assert 'File search' in rv.data
        assert 'Code search' in rv.data

        rv = self.app.get('/doc/overview/')
        assert 'Debsources provides Web access' in rv.data
        
        rv = self.app.get('/doc/api/')
        assert 'API documentation' in rv.data
        
        rv = self.app.get('/doc/url/')
        assert 'URL scheme' in rv.data

        rv = self.app.get('/about/')
        assert 'source code is available' in rv.data

    def test_packages_list(self):
        rv = json.loads(self.app.get('/api/list/').data)
        assert {'name': "libcaca"} in rv['packages']
        assert len(rv['packages']) == 14
    
    def test_by_prefix(self):
        rv = json.loads(self.app.get('/api/prefix/libc/').data)
        assert {'name': "libcaca"} in rv['packages']

    def test_package(self):
        rv = json.loads(self.app.get('/api/src/ledit/').data)
        assert rv['path'] == "ledit"
        assert len(rv['versions']) == 3
        assert rv['type'] == "package"
        
    def test_folder(self):
        rv = json.loads(self.app.get('/api/src/ledit/2.01-6/').data)
        assert rv['type'] == "directory"
        assert rv['path'] == "ledit/2.01-6"
        assert rv['package'] == "ledit"
        assert rv['directory'] == "2.01-6"
        assert {'type': "file", 'name': "ledit.ml"} in rv['content']
        
    def test_source_file(self):
        rv = self.app.get('/src/ledit/2.01-6/ledit.ml/')
        
        # source code detection
        assert '<code id="sourcecode" class="ocaml">' in rv.data
        
        # highlight.js present?
        assert 'hljs.highlightBlock' in rv.data
        assert ('<script src="/javascript/highlight/highlight.pack.js">'
                '</script>') in rv.data
        
        # content of the file
        assert 'Institut National de Recherche en Informatique' in rv.data
        
        # correct number of lines
        assert '1506 lines' in rv.data
        
        # permissions of the file
        assert 'permissions: rw-r--r--' in rv.data
        
        # raw file link
        assert ('<a href="/data/main/l/ledit/2.01-6/ledit.ml">'
                'download</a>') in rv.data
        
        # parent folder link
        assert '<a href="/src/ledit/2.01-6/">parent folder</a>' in rv.data
    
    def test_source_file_text(self):
        rv = self.app.get('/src/ledit/2.01-6/README/')
        assert '<code id="sourcecode" class="no-highlight">' in rv.data
        
    def test_source_file_embedded(self):
        rv = self.app.get('/embed/file/ledit/2.01-6/ledit.ml/')
        assert '<code id="sourcecode" class="ocaml">' in rv.data
        assert 'Institut National de Recherche en Informatique' in rv.data
        assert '<div id="logo">' not in rv.data
        
    def test_errors(self):
        rv = json.loads(self.app.get('/api/src/blablabla/').data)
        assert rv['error'] == 404
        
    def test_latest(self):
        rv = json.loads(self.app.get('/api/src/ledit/latest/',
                                     follow_redirects=True).data)
        assert "2.03-2" in rv['path']
    
    def test_codesearch_box(self):
        rv = self.app.get('/src/ledit/2.03-2/ledit.ml/')
        assert 'value="package:ledit "' in rv.data
    
    def test_pagination(self):
        rv = self.app.get('/list/2/')
        assert '<a href="/list/1/">&laquo; Previous</a>' in rv.data
        assert '<a href="/list/3/">Next &raquo;</a>' in rv.data
        assert '<strong>2</strong>' in rv.data
    
    def test_file_duplicates(self):
        rv = json.loads(self.app.get('/api/src/bsdgames-nonfree/'
                                     '2.17-3/COPYING/').data)
        assert rv["number_of_duplicates"] == 3
        assert rv["checksum"] == ("be43f81c20961702327c10e9bd5f5a9a2b1cc"
                                  "eea850402ea562a9a76abcfa4bf")
    
    def test_checksum_search(self):
        rv = json.loads(self.app.get('/api/sha256/?checksum=be43f81c20961702327'
                                     'c10e9bd5f5a9a2b1cceea850402ea562a9a76abcf'
                                     'a4bf&page=1').data)
        assert rv["count"] == 3
        assert len(rv["results"]) == 3
    
    def test_checksum_search_within_package(self):
        rv = json.loads(self.app.get('/api/sha256/?checksum=4f721b8e5b0add185d6'
                                     'af7a93e577638d25eaa5c341297d95b4a27b7635b'
                                     '4d3f&package=susv2').data)
        assert rv["count"] == 1
    
    def test_search_ctag(self):
        rv = json.loads(self.app.get('/api/ctag/?ctag=name').data)
        assert rv["count"] == 88
        assert len(rv["results"]) == 88
    
    def test_search_ctag_within_package(self):
        rv = json.loads(self.app.get('/api/ctag/?ctag=name&package=ledger').data)
        assert rv["count"] == 14
        assert len(rv["results"]) == 14
    
    def test_pkg_infobox(self):
        rv = json.loads(self.app.get('/api/src/libcaca/0.99.beta17-1/').data)
        assert rv["pkg_infos"]["suites"] == ["squeeze"]
        assert rv["pkg_infos"]["area"] == "main"
        assert rv["pkg_infos"]["sloc"][0] == ["ansic", 22607]
        assert rv["pkg_infos"]["metric"]["size"] == 6584
        assert rv["pkg_infos"]["vcs_browser"] == (
            "http://svn.debian.org/wsvn/sam-hocevar/pkg-misc/unstable/libcaca/")
        assert rv["pkg_infos"]["vcs_type"] == "svn"
        assert rv["pkg_infos"]["pts_link"] == (
            "http://tracker.debian.org/pkg/libcaca")
    
    def test_pkg_infobox_embed(self):
        rv = self.app.get('/embed/pkginfo/libcaca/0.99.beta17-1/')
        assert '<div id="pkginfobox" class="pkginfobox_large">' in rv.data
        assert '<footer' not in rv.data # it's an infobox-only page
    
    def test_info_version(self):
        rv = self.app.get('/info/package/libcaca/0.99.beta17-1/')
        assert '<div id="pkginfobox" class="pkginfobox_large">' in rv.data
    
    def test_stats_suite(self):
        rv = json.loads(self.app.get('/api/stats/jessie/').data)
        assert rv["suite"] == "jessie"
        # assert rv["results"]["debian_jessie.ctags"] == 21767
        # assert rv["results"]["debian_jessie.disk_usage"] == 43032
        assert rv["results"]["debian_jessie.source_files"] == 1677
        assert rv["results"]["debian_jessie.sloccount.python"] == 2916
    
    def test_stats_all(self):
        rv = json.loads(self.app.get('/api/stats/').data)
        assert sorted(rv["all_suites"]) == (
            ["debian_experimental", "debian_jessie", "debian_sid",
             "debian_squeeze", "debian_wheezy"])
        assert "ansic" in rv["languages"]
        assert rv["results"]["debian_sid.sloccount.ansic"] == 140353

    def test_suggestions_when_404(self):
        rv = self.app.get('/src/libcaca/0.NOPE.beta17-1/src/cacaview.c/')
        assert 'other versions of this package are available' in rv.data
        assert '<a href="/src/libcaca/0.99.beta17-1/src/cacaview.c/">' in rv.data

if __name__ == '__main__':
    unittest.main(exit=False)
