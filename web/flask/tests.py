import os
import app
#from app import db
import unittest
import tempfile
#from app.models_app import Package_app

class FlaskrTestCase(unittest.TestCase):

    def setUp(self):
        # TODO: database
        self.db_fd, dbtmp = tempfile.mkstemp()
        #app.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+dbtmp
        #app.app.config['TESTING'] = True
        #app.app.config['SQLALCHEMY_ECHO'] = False
        #hello = Package_app("hello")
        #db.session.add(hello)
        #db.session.commit()
        
        self.app = app.app.test_client()
        #app.init_db()

    def tearDown(self):
        #os.close(self.db_fd)
        #os.unlink(app.app.config['SQLALCHEMY_DATABASE_URI'])
        pass

    def test_index_page(self):
        rv = self.app.get('/')
        assert 'Debsources' in rv.data
        
    def test_left_menu(self):
        rv = self.app.get('/')
        assert '<a href="/prefix/libz/">libz</a>' in rv.data
        assert '<form action="/search/"' in rv.data

    def test_doc_pages(self):
        rv = self.app.get('/doc/')
        assert 'Documentation' in rv.data
        rv = self.app.get('/doc/api/')
        assert 'API documentation' in rv.data
        rv = self.app.get('/doc/url/')
        assert 'URL scheme' in rv.data
        
    def test_footer(self):
        rv = self.app.get('/')
        assert 'Copyright' in rv.data
        assert 'GNU AGPL' in rv.data

    def test_search(self):
        pass
        #rv = self.app.get('/search/hello/')
        #assert 'Search: hello' in rv.data
        # TODO: insert arbitrary values and check their existence in results

if __name__ == '__main__':
    unittest.main()
