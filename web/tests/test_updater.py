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

import logging
import os
import shutil
import sqlalchemy
import subprocess
import tempfile
import unittest

from nose.tools import istest
from nose.plugins.attrib import attr
from os.path import abspath, dirname

import mainlib
import models
import updater

from dbhelpers import DbTestFixture, pg_dump, TEST_DB_NAME
from testdata import *


def compare_dirs(dir1, dir2, exclude=[]):
    """recursively compare dir1 with dir2

    return (True, None) if they are the same or a (False, diff) where diff is a
    textual list of files that differ (as per "diff --brief")

    """
    try:
        subprocess.check_output(['diff', '-Naur', '--brief'] +
                                [ '--exclude=' + pat for pat in exclude ] +
                                [dir1, dir2])
        return True, None
    except subprocess.CalledProcessError, e:
        return False, e.output


def mk_conf(tmpdir):
    """return a debsources updater configuration that works in a temp dir

    for testing purposes

    """
    conf = {
        'bin_dir': abspath(os.path.join(TEST_DIR, '../../bin')),
        'cache_dir': os.path.join(tmpdir, 'cache'),
        'db_uri': 'postgresql:///' + TEST_DB_NAME,
        'dry_run': False,
        'expire_days': 0,
        'force_triggers': '',
        'hooks': ['sloccount', 'checksums', 'ctags', 'metrics'],
        'mirror_dir': os.path.join(TEST_DATA_DIR, 'mirror'),
        'passes': set(['hooks.fs', 'hooks', 'fs', 'db', 'hooks.db']),
        'python_dir': abspath(os.path.join(TEST_DIR, '..')),
        'root_dir': abspath(os.path.join(TEST_DIR, '../..')),
        'sources_dir': os.path.join(tmpdir, 'sources'),
    }
    return conf


@attr('infra')
@attr('postgres')
@attr('slow')
class Updater(unittest.TestCase, DbTestFixture):

    def setUp(self):
        self.db_setup()
        self.tmpdir = tempfile.mkdtemp(suffix='.debsources-test')

    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)

    @istest
    def updaterProducesReferenceDb(self):
        # move tables to reference schema 'ref' and recreate them under 'public'
        self.session.execute('CREATE SCHEMA ref');
        for tblname, table in models.Base.metadata.tables.items():
            self.session.execute('ALTER TABLE %s SET SCHEMA ref' % tblname)
            self.session.execute(sqlalchemy.schema.CreateTable(table))

        # do a full update run in a virtual test environment
        conf = mk_conf(self.tmpdir)
        mainlib.init_logging(conf, console_verbosity=logging.WARNING)
        (observers, file_exts)  = mainlib.load_hooks(conf)
        updater.update(conf, self.session, observers)

        # sources/ dir comparison. Ignored patterns:
        # - plugin result caches -> because most of them are in os.walk()
        #   order, which is not stable
        # - dpkg-source log stored in *.log
        exclude_pat = [ '*' + ext for ext in file_exts ] + [ '*.log' ]
        dir_eq, dir_diff = compare_dirs(os.path.join(self.tmpdir, 'sources'),
                                        os.path.join(TEST_DATA_DIR, 'sources'),
                                        exclude=exclude_pat)
        if not dir_eq:
            print dir_diff
        self.assertTrue(dir_eq)

        # DB comparison
        for tblname in models.Base.metadata.tables.keys():
            if tblname == 'metrics':	# metrics are not stable due to 'du'
                continue
            if tblname == 'ctags':	# XXX LargeBinary seem incomparable
                continue
            if tblname == 'checksums':	# XXX LargeBinary seem incomparable
                continue
            ref_tblname = 'ref.' + tblname
            for (t1, t2) in [(tblname, ref_tblname), (ref_tblname, tblname)]:
                diff = self.session.execute(
                    'SELECT * FROM %s EXCEPT SELECT * FROM %s' % (t1, t2))
                if diff.rowcount > 0:
                    print 'row in %s but not %s db (sample):' % (t1, t2), \
                        diff.fetchone()
                    self.session.rollback()
                    (_f, dumppath) = tempfile.mkstemp(suffix='.debsources-dump')
                    pg_dump(TEST_DB_NAME, dumppath)
                    print 'test db dump saved as %s' % dumppath
                self.assertEqual(diff.rowcount, 0,
                                 msg='%d rows in %s \ %s' % (diff.rowcount, t1, t2))


@attr('infra')
@attr('cache')
@attr('metadata')
class MetadataCache(unittest.TestCase, DbTestFixture):
    """tests for on-disk cache of debsources metadata

    usually stored in cache/stats.data

    """

    @staticmethod
    def parse_stats(fname):
        """return the parsed content of stats.data as a dictionary"""
        stats = {}
        for line in open(fname):
            k, v = line.split()
            stats[k] = int(v)
        return stats

    def setUp(self):
        self.db_setup()
        self.tmpdir = tempfile.mkdtemp(suffix='.debsources-test')
        self.conf = mk_conf(self.tmpdir)
        updater.update_statistics(self.conf, self.session)
        self.stats = self.parse_stats(
            os.path.join(self.conf['cache_dir'], 'stats.data'))

    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)

    @istest
    def sizeMatchesReferenceDb(self):
        EXPECTED_SIZE = 122628
        self.assertEqual(EXPECTED_SIZE, self.stats['size'])

    @istest
    def sloccountsMatchReferenceDb(self):
        EXPECTED_STATS = {	# just a few samples
            'size.debian_experimental': 6520,
            'sloccount.awk.debian_sid': 25,
            'sloccount.cpp.debian_sid': 41458,
            'sloccount.cpp.debian_squeeze': 36508,
            'sloccount.cpp.debian_wheezy': 37375,
            'sloccount.perl': 1838,
            'sloccount.python': 7760,
            'sloccount.python.debian_wheezy': 2798,
            'sloccount.ruby.debian_squeeze': 193,
            'sloccount.ruby.debian_wheezy': 193,
        }
        for k, v in EXPECTED_STATS.iteritems():
            self.assertEqual(EXPECTED_STATS[k], self.stats[k])
