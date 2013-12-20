from app import views	# XXX work around while we fix circular import

import models
import os
import sqlalchemy
import subprocess
import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

TEST_DB = 'debsources-test'
TEST_DB_DUMP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data/db/pg-dump-custom')
TEST_DB_URI = 'postgresql:///%s' % TEST_DB


def pg_restore(dbname, dumpfile):
    subprocess.check_call(['pg_restore', '--dbname', dbname, dumpfile])


@attr('infra')
@attr('postgres')
@attr('slow')
class Db(unittest.TestCase):

    def setUp(self):
        self.db = sqlalchemy.create_engine(TEST_DB_URI)
        models.Base.metadata.drop_all(self.db)	# just in case...
        pg_restore(TEST_DB, TEST_DB_DUMP)
        self.Session = sqlalchemy.orm.sessionmaker()
        self.session = self.Session(bind=self.db)
        # models.Base.metadata.create_all(self.db)

    def tearDown(self):
        models.Base.metadata.drop_all(self.db)
        # self.session.rollback()
        # self.session.close()

    def testDummy(self):
        pass

    # @istest
    # def updaterProducesReferenceDb():
    #     pass	# TODO
