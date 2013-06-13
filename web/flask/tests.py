import os
import sys
import unittest
import tempfile
import json


from app import app

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)
from scripts import sources2db


class DebsourcesTestCase(unittest.TestCase):
    ClassIsSetup = False
    
    def setUp(self):
        # from http://stezz.blogspot.fr
        # /2011/04/calling-only-once-setup-in-unittest-in.html
        
        # If it was not setup yet, do it
        if not self.ClassIsSetup:
            print "Initializing testing environment"
            # run the real setup
            self.setupClass()
            # remember that it was setup already
            self.__class__.ClassIsSetup = True
    
    def setupClass(self):
        
        url = "sqlite:///" + os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "tests/app.db")
        sources2db.sources2db("tests/sources.txt", url,
                              drop=True, verbose=False)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_ECHO'] = False
        
        app.config['SQLALCHEMY_DATABASE_URI'] = url #"sqlite:///:memory:"
        self.__class__.app = app.test_client()
        
        
    def tearDown(self):
        pass
        
    def test_search(self):        
        rv = json.loads(self.app.get('/api/search/vcar/').data)
        assert rv['query'] == 'vcar'
        assert rv['results']['exact'] is None
        assert {'name': "2vcard"} in rv['results']['other']
        
    def test_static_pages(self):
        rv = self.app.get('/')
        assert 'Debsources' in rv.data
        
        rv = self.app.get('/doc/api/')
        assert 'API documentation' in rv.data
        
        rv = self.app.get('/doc/url/')
        assert 'URL scheme' in rv.data
        
    def test_packages_list(self):
        rv = json.loads(self.__class__.app.get('/api/list/').data)
        assert {'name': "2vcard"} in rv['packages']

    def test_package(self):
        rv = json.loads(self.app.get('/api/src/0ad').data)
        assert rv['path'] == "0ad"
        assert rv['pts_link'] == "http://packages.qa.debian.org/0ad"
        assert len(rv['versions']) == 2
        assert rv['type'] == "package"
        
    def test_folder(self):
        app.config['SOURCES_FOLDER'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "tests/sources")
        rv = json.loads(self.app.get('/api/src/0ad/0.0.13-2').data)
        assert rv['type'] == "directory"
        assert {'type': "file", 'name': "hello.c"} in rv['content']
        
    def test_source_file(self):
        app.config['SOURCES_FOLDER'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "tests/sources")
        rv = self.app.get('/src/0ad/0.0.13-2/NetStats.cpp')
        print rv.data
        assert '<code id="sourcecode" class="cpp">' in rv.data
        assert 'size_t CNetStatsTable::GetNumberRows()' in rv.data

if __name__ == '__main__':
    already_setup = False
    unittest.main()
