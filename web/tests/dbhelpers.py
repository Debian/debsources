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

import os
import sqlalchemy
import subprocess

from os.path import abspath, dirname

import models


THIS_DIR = dirname(abspath(__file__))

TEST_DB_NAME = 'debsources-test'
TEST_DB_DUMP = os.path.join(THIS_DIR, 'data/db/pg-dump-custom')


def pg_restore(dbname, dumpfile):
    subprocess.check_call(['pg_restore', '--dbname', dbname, dumpfile])

def pg_dump(dbname, dumpfile):
    subprocess.check_call(['pg_dump', '--no-owner', '--no-privileges', '-Fc',
                           '-f', dumpfile, dbname])


class DbTestFixture(object):

    def db_setup(self, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
        self.db = sqlalchemy.create_engine('postgresql:///' + dbname, echo=echo)
        models.Base.metadata.drop_all(self.db)	# just in case...
        pg_restore(dbname, dbdump)
        self.Session = sqlalchemy.orm.sessionmaker()
        self.session = self.Session(bind=self.db)
        # models.Base.metadata.create_all(self.db)

    def db_teardown(self):
        self.session.rollback()
        self.session.close()
        models.Base.metadata.drop_all(self.db)
