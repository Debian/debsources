# Copyright (C) 2013-2014  Stefano Zacchiroli <zack@upsilon.cc>
#                    2014  Matthieu Caneill <matthieu.caneill@gmail.com>
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

# queries to compare two DB schemas (e.g. "public.*" and "ref.*")
DB_COMPARE_QUERIES = {
    "package_names":
    "SELECT name \
     FROM %(schema)s.package_names \
     ORDER BY name \
     LIMIT 100",

    "packages":
    "SELECT package_names.name, version, area, vcs_type, vcs_url, vcs_browser \
     FROM %(schema)s.packages, %(schema)s.package_names \
     WHERE packages.name_id = package_names.id \
     ORDER BY package_names.name, version \
     LIMIT 100",

    "suites":
    "SELECT package_names.name, packages.version, suite \
     FROM %(schema)s.packages, %(schema)s.package_names, %(schema)s.suites \
     WHERE packages.name_id = package_names.id \
     AND suites.package_id = packages.id \
     ORDER BY package_names.name, packages.version, suite \
     LIMIT 100",

    "files":
    "SELECT package_names.name, packages.version, files.path \
     FROM %(schema)s.files, %(schema)s.packages, %(schema)s.package_names \
     WHERE packages.name_id = package_names.id \
     AND files.package_id = packages.id \
     ORDER BY package_names.name, packages.version, files.path \
     LIMIT 100",

    "checksums":
    "SELECT package_names.name, packages.version, files.path, sha256 \
     FROM %(schema)s.files, %(schema)s.packages, %(schema)s.package_names, %(schema)s.checksums \
     WHERE packages.name_id = package_names.id \
     AND checksums.package_id = packages.id \
     AND checksums.file_id = files.id \
     ORDER BY package_names.name, packages.version, files.path \
     LIMIT 100",

    "sloccounts":
    "SELECT package_names.name, packages.version, language, count \
     FROM %(schema)s.sloccounts, %(schema)s.packages, %(schema)s.package_names \
     WHERE packages.name_id = package_names.id \
     AND sloccounts.package_id = packages.id \
     ORDER BY package_names.name, packages.version, language \
     LIMIT 100",

    "ctags":
    "SELECT package_names.name, packages.version, files.path, tag, line, kind, language \
     FROM %(schema)s.ctags, %(schema)s.files, %(schema)s.packages, %(schema)s.package_names \
     WHERE packages.name_id = package_names.id \
     AND ctags.package_id = packages.id \
     AND ctags.file_id = files.id \
     ORDER BY package_names.name, packages.version, files.path, tag, line, kind, language \
     LIMIT 100",

    "metric":
    "SELECT package_names.name, packages.version, metric, value_ \
     FROM %(schema)s.metrics, %(schema)s.packages, %(schema)s.package_names \
     WHERE packages.name_id = package_names.id \
     AND metrics.package_id = packages.id \
     AND metric != 'size' \
     ORDER BY package_names.name, packages.version, metric \
     LIMIT 100",

    # XXX projecting also on the ctags column gives different result (by a few
    # units), even if the actual ctags tables are identical. WTH ?!?!
    "history_size":
    "SELECT suite, source_packages, binary_packages, source_files \
     FROM %(schema)s.history_size \
     ORDER BY timestamp, suite",

    "history_sloccount":
    "SELECT suite, \
       lang_ansic, lang_cpp, lang_lisp, lang_erlang, lang_python, lang_yacc \
     FROM %(schema)s.history_sloccount \
     ORDER BY timestamp, suite",
}



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

def db_setup(test_subj, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
    """Sets up the db for use by a given test subject.

    test_subj must be an instance of DbTestFixture (or inheritated class),
    or the class itself. This allows using db_setup by
    - unittest setUp (instance method), or
    - unittest setUpClass (class method).

    """
    try:
        pg_createdb(dbname)
    except subprocess.CalledProcessError:	# try recovering once, in case
        pg_dropdb(dbname)			# the db already existed
        pg_createdb(dbname)
    test_subj.dbname = dbname
    test_subj.db = sqlalchemy.create_engine(
        'postgresql:///' + dbname, echo=echo)
    pg_restore(dbname, dbdump)
    Session = sqlalchemy.orm.sessionmaker()
    test_subj.session = Session(bind=test_subj.db)

def db_teardown(test_subj):
    """Tears down db support used by a given test subject.

    test_subj must be an instance of DbTestFixture (or inheritated class), or
    the class itself. See db_setup for further discussion

    """
    test_subj.session.rollback()
    test_subj.session.close()
    test_subj.db.dispose()
    pg_dropdb(test_subj.dbname)


class DbTestFixture(object):
    """mix this in a given test subject to have DB fixture support"""

    def db_setup(self, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
        db_setup(self, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False)

    @classmethod
    def db_setup_cls(cls, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False):
        db_setup(cls, dbname=TEST_DB_NAME, dbdump=TEST_DB_DUMP, echo=False)

    def db_teardown(self):
        db_teardown(self)
    
    @classmethod
    def db_teardown_cls(cls):
        db_teardown(cls)
