# Copyright (C) 2013-2014  Stefano Zacchiroli <zack@upsilon.cc>
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

from subprocess_workaround import subprocess_setup
from testdata import *


TEST_DB_DUMP = os.path.join(TEST_DATA_DIR, 'db/pg-dump-custom')


def pg_restore(dbname, dumpfile):
    subprocess.check_call(['pg_restore', '--no-owner', '--no-privileges',
                           '--dbname', dbname, dumpfile],
                          preexec_fn=subprocess_setup)

def pg_dump(dbname, dumpfile):
    subprocess.check_call(['pg_dump', '--no-owner', '--no-privileges', '-Fc',
                           '-f', dumpfile, dbname],
                          preexec_fn=subprocess_setup)

def pg_dropdb(dbname):
    subprocess.check_call(['dropdb', dbname],
                          preexec_fn=subprocess_setup)

def pg_createdb(dbname):
    subprocess.check_call(['createdb', dbname],
                          preexec_fn=subprocess_setup)

def db_setup(obj_or_cls, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
    """
    Sets up the db.
    obj_or_cls must be an instance of DbTestFixture (or inheritated class),
    or the class itself. This allows using db_setup by
    - unittest setUp (instance method), or
    - unittest setUpClass (class method).
    """
    try:
        pg_createdb(dbname)
    except subprocess.CalledProcessError:	# try recovering once, in case
        pg_dropdb(dbname)			# the db already existed
        pg_createdb(dbname)
    obj_or_cls.dbname = dbname
    obj_or_cls.db = sqlalchemy.create_engine(
        'postgresql:///' + dbname, echo=echo)
    pg_restore(dbname, dbdump)
    Session = sqlalchemy.orm.sessionmaker()
    obj_or_cls.session = Session(bind=obj_or_cls.db)

def db_teardown(obj_or_class):
    """
    Closes the db session and removes the db.
    Same problematic with instance/class than for db_setup().
    """
    obj_or_class.session.rollback()
    obj_or_class.session.close()
    obj_or_class.db.dispose()
    pg_dropdb(obj_or_class.dbname)

class DbTestFixture(object):

    def db_setup(self, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
        db_setup(self, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False)

    @classmethod
    def db_setup(cls, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
        db_setup(cls, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False)

    def db_teardown(self):
        db_teardown(self)
    
    @classmethod
    def db_teardown(cls):
        db_teardown(cls)


