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

from db_testing import DbTestFixture, pg_dump
from subprocess_workaround import subprocess_setup
from testdata import *


# queries to compare two DB schemas (e.g. "public.*" and "ref.*")
DB_COMPARE_QUERIES = {
    "packages":
    "SELECT name \
     FROM %(schema)s.packages \
     ORDER BY name \
     LIMIT 100",

    "versions":
    "SELECT packages.name, vnumber, area, vcs_type, vcs_url, vcs_browser \
     FROM %(schema)s.versions, %(schema)s.packages \
     WHERE versions.package_id = packages.id \
     ORDER BY packages.name, vnumber \
     LIMIT 100",

    "suitesmapping":
    "SELECT packages.name, versions.vnumber, suite \
     FROM %(schema)s.versions, %(schema)s.packages, %(schema)s.suitesmapping \
     WHERE versions.package_id = packages.id \
     AND suitesmapping.sourceversion_id = versions.id \
     ORDER BY packages.name, versions.vnumber, suite \
     LIMIT 100",

    "files":
    "SELECT packages.name, versions.vnumber, files.path \
     FROM %(schema)s.files, %(schema)s.versions, %(schema)s.packages \
     WHERE versions.package_id = packages.id \
     AND files.version_id = versions.id \
     ORDER BY packages.name, versions.vnumber, files.path \
     LIMIT 100",

    "checksums":
    "SELECT packages.name, versions.vnumber, files.path, sha256 \
     FROM %(schema)s.files, %(schema)s.versions, %(schema)s.packages, %(schema)s.checksums \
     WHERE versions.package_id = packages.id \
     AND checksums.version_id = versions.id \
     AND checksums.file_id = files.id \
     ORDER BY packages.name, versions.vnumber, files.path \
     LIMIT 100",

    "sloccounts":
    "SELECT packages.name, versions.vnumber, language, count \
     FROM %(schema)s.sloccounts, %(schema)s.versions, %(schema)s.packages \
     WHERE versions.package_id = packages.id \
     AND sloccounts.sourceversion_id = versions.id \
     ORDER BY packages.name, versions.vnumber, language \
     LIMIT 100",

    "ctags":
    "SELECT packages.name, versions.vnumber, files.path, tag, line, kind, language \
     FROM %(schema)s.ctags, %(schema)s.files, %(schema)s.versions, %(schema)s.packages \
     WHERE versions.package_id = packages.id \
     AND ctags.version_id = versions.id \
     AND ctags.file_id = files.id \
     ORDER BY packages.name, versions.vnumber, files.path, tag, line, kind, language \
     LIMIT 100",

    "metric":
    "SELECT packages.name, versions.vnumber, metric, value_ \
     FROM %(schema)s.metrics, %(schema)s.versions, %(schema)s.packages \
     WHERE versions.package_id = packages.id \
     AND metrics.sourceversion_id = versions.id \
     AND metric != 'size' \
     ORDER BY packages.name, versions.vnumber, metric \
     LIMIT 100",
}


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

    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)

    def do_update(self):
        """do a full update run in a virtual test environment"""
        mainlib.init_logging(self.conf, console_verbosity=logging.WARNING)
        (observers, file_exts)  = mainlib.load_hooks(self.conf)
        updater.update(self.conf, self.session, observers)
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
        self.assertEqual(EXPECTED_SIZE, self.stats['size.du'])

    @istest
    def statsMatchReferenceDb(self):
        expected_stats = {	# just a few samples
            'ctags': 70166,
            'ctags.debian_sid': 21395,
            'ctags.debian_squeeze': 30633,
            'size.du.debian_experimental': 6520,
            'size.source_files': 5489,
            'size.source_files.debian_experimental': 645,
            'size.source_files.debian_jessie': 1677,
            'size.versions': 31,
            'size.versions.debian_squeeze': 13,
            'size.versions.debian_wheezy': 12,
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
        self.assertDictContainsSubset(expected_stats, self.stats)
