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

from db_testing import DbTestFixture, pg_dump, DB_COMPARE_QUERIES
from subprocess_workaround import subprocess_setup
from testdata import *


def compare_dirs(dir1, dir2, exclude=[]):
    """recursively compare dir1 with dir2

    return (True, None) if they are the same or a (False, diff) where diff is a
    textual list of files that differ (as per "diff --brief")

    """
    try:
        subprocess.check_output(['diff', '-Naur', '--brief'] +
                                [ '--exclude=' + pat for pat in exclude ] +
                                [dir1, dir2],
                                preexec_fn=subprocess_setup)
        return True, None
    except subprocess.CalledProcessError, e:
        return False, e.output


def compare_files(file1, file2):
    """compare file1 and file2 with diff

    return (True, None) if they are the same or a (False, diff) where diff is a
    textual diff between the two (as per "diff -u")

    """
    try:
        subprocess.check_output(['diff', '-Nu', file1, file2],
                                preexec_fn=subprocess_setup)
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
        'single_transaction': 'true',
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


def db_mv_tables_to_schema(session, new_schema):
    """move all debsources tables from the 'public' schema to new_schema

    then recreate the corresponding (empty) tables under 'public'
    """
    session.execute('CREATE SCHEMA %s' % new_schema);
    for tblname, table in models.Base.metadata.tables.items():
        session.execute('ALTER TABLE %s SET SCHEMA %s' \
                        % (tblname, new_schema))
        session.execute(sqlalchemy.schema.CreateTable(table))


def assert_db_schema_equal(test_subj, expected_schema, actual_schema):
    for tbl, q in DB_COMPARE_QUERIES.iteritems():
        expected = [ dict(r.items()) for r in \
                     test_subj.session.execute(q % {'schema': expected_schema}) ]
        actual = [ dict(r.items()) for r in \
                   test_subj.session.execute(q % {'schema': actual_schema}) ]
        test_subj.assertSequenceEqual(expected, actual,
                        msg='table %s differs from reference' % tbl)

def assert_dir_equal(test_subj, dir1, dir2, exclude=[]):
    dir_eq, dir_diff = compare_dirs(dir1, dir2, exclude)
    if not dir_eq:
        print dir_diff
    test_subj.assertTrue(dir_eq, 'file system storages differ')


@attr('infra')
@attr('postgres')
class Updater(unittest.TestCase, DbTestFixture):

    def setUp(self):
        self.db_setup()
        self.tmpdir = tempfile.mkdtemp(suffix='.debsources-test')
        self.conf = mk_conf(self.tmpdir)
        self.longMessage = True
        self.maxDiff = None

    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)

    TEST_STAGES = updater.UPDATE_STAGES - set([updater.STAGE_CHARTS])

    def do_update(self, stages=TEST_STAGES):
        """do a full update run in a virtual test environment"""
        mainlib.init_logging(self.conf, console_verbosity=logging.WARNING)
        (observers, file_exts)  = mainlib.load_hooks(self.conf)
        updater.update(self.conf, self.session, observers, stages)
        return file_exts

    @istest
    @attr('slow')
    def updaterProducesReferenceDb(self):
        db_mv_tables_to_schema(self.session, 'ref')
        file_exts = self.do_update()

        # sources/ dir comparison. Ignored patterns:
        # - plugin result caches -> because most of them are in os.walk()
        #   order, which is not stable
        # - dpkg-source log stored in *.log
        exclude_pat = [ '*' + ext for ext in file_exts ] + [ '*.log' ]
        assert_dir_equal(self,
                         os.path.join(self.tmpdir, 'sources'),
                         os.path.join(TEST_DATA_DIR, 'sources'),
                         exclude=exclude_pat)

        assert_db_schema_equal(self, 'ref', 'public')


    @istest
    def updaterProducesReferenceSourcesTxt(self):
        def parse_sources_txt(fname):
            for line in open(fname):
                fields = line.split()
                if fields[3].startswith('/'):
                    fields[3] = os.path.relpath(fields[3], self.conf['mirror_dir'])
                if fields[4].startswith('/'):
                    fields[4] = os.path.relpath(fields[4], self.conf['sources_dir'])
                yield fields

        # given DB is pre-filled, this should be a "do-almost-nothing" update
        self.do_update()
        srctxt_path = 'cache/sources.txt'
        actual_srctxt = list(parse_sources_txt(os.path.join(self.tmpdir, srctxt_path)))
        expected_srctxt = list(parse_sources_txt(os.path.join(TEST_DATA_DIR, srctxt_path)))
        self.assertItemsEqual(actual_srctxt, expected_srctxt)


    @istest
    @attr('slow')
    def updaterRecreatesDbFromFiles(self):
        orig_sources = os.path.join(TEST_DATA_DIR, 'sources')
        dest_sources = os.path.join(self.tmpdir, 'sources')
        shutil.copytree(orig_sources, dest_sources)
        db_mv_tables_to_schema(self.session, 'ref')

        self.conf['passes'] = set(['db', 'hooks', 'hooks.db'])
        self.do_update()

        # check that the update didn't touch filesystem storage
        assert_dir_equal(self, orig_sources, dest_sources)
        # check that the update recreate an identical DB
        assert_db_schema_equal(self, 'ref', 'public')


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
        dummy_status = updater.UpdateStatus()
        updater.update_statistics(dummy_status, self.conf, self.session)
        self.stats = self.parse_stats(
            os.path.join(self.conf['cache_dir'], 'stats.data'))

    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)

    @istest
    def sizeMatchesReferenceDb(self):
        EXPECTED_SIZE = 122628
        self.assertEqual(EXPECTED_SIZE, self.stats['total.disk_usage'])

    @istest
    def statsMatchReferenceDb(self):
        expected_stats = {	# just a few samples
            'total.ctags': 70166,
            'debian_sid.ctags': 21395,
            'debian_squeeze.ctags': 30633,
            'debian_experimental.disk_usage': 6520,
            'total.source_files': 5489,
            'debian_experimental.source_files': 645,
            'debian_jessie.source_files': 1677,
            'total.source_packages': 31,
            'debian_squeeze.source_packages': 13,
            'debian_wheezy.source_packages': 12,
            'debian_sid.sloccount.awk': 25,
            'debian_sid.sloccount.cpp': 41458,
            'debian_squeeze.sloccount.cpp': 36508,
            'debian_wheezy.sloccount.cpp': 37375,
            'total.sloccount.perl': 1838,
            'total.sloccount.python': 7760,
            'debian_wheezy.sloccount.python': 2798,
            'debian_squeeze.sloccount.ruby': 193,
            'debian_wheezy.sloccount.ruby': 193,
        }
        self.assertDictContainsSubset(expected_stats, self.stats)
