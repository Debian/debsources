from app import views	# XXX work around while we fix circular import

import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

import mainlib
import models
import os

from dbhelpers import DbTestFixture


TEST_DB_NAME = 'debsources-test'
TEST_DB_DUMP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'data/db/pg-dump-custom')

@attr('infra')
@attr('postgres')
@attr('slow')
class Db(unittest.TestCase, DbTestFixture):

    def setUp(self):
        self.db_setup(TEST_DB_NAME, TEST_DB_DUMP)

    def tearDown(self):
        self.db_teardown()

    def testDummy(self):
        pass

    # @istest
    # def updaterProducesReferenceDb():
    #     pass	# TODO
