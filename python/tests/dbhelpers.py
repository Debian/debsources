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
import signal
import sqlalchemy
import subprocess

from os.path import abspath, dirname

import models

from testdata import *


TEST_DB_DUMP = os.path.join(TEST_DATA_DIR, 'db/pg-dump-custom')


def _subprocess_setup():
    """SIGPIPE handling work-around. See http://bugs.python.org/issue1652

    """
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def pg_restore(dbname, dumpfile):
    subprocess.check_call(['pg_restore', '--no-owner', '--no-privileges',
                           '--dbname', dbname, dumpfile],
                          preexec_fn=_subprocess_setup)

def pg_dump(dbname, dumpfile):
    subprocess.check_call(['pg_dump', '--no-owner', '--no-privileges', '-Fc',
                           '-f', dumpfile, dbname],
                          preexec_fn=_subprocess_setup)

def pg_dropdb(dbname):
    subprocess.check_call(['dropdb', dbname],
                          preexec_fn=_subprocess_setup)

def pg_createdb(dbname):
    subprocess.check_call(['createdb', dbname],
                          preexec_fn=_subprocess_setup)


class DbTestFixture(object):

    def db_setup(self, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
        try:
            pg_createdb(dbname)
        except subprocess.CalledProcessError:	# try recovering once, in case
            pg_dropdb(dbname)			# the db already existed
            pg_createdb(dbname)
        self.dbname = dbname
        self.db = sqlalchemy.create_engine('postgresql:///' + dbname, echo=echo)
        pg_restore(dbname, dbdump)
        Session = sqlalchemy.orm.sessionmaker()
        self.session = Session(bind=self.db)

    def db_teardown(self):
        self.session.rollback()
        self.session.close()
        self.db.dispose()
        pg_dropdb(self.dbname)
