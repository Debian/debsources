# Copyright (C) 2013  Stefano Zacchiroli <zack@upsilon.cc>
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
