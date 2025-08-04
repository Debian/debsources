# Copyright (C) 2013-2021  The Debsources developers
# <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


import glob
import logging
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import sqlalchemy
from nose.plugins.attrib import attr
from nose.tools import istest

from debsources import db_storage, mainlib, models, statistics, updater
from debsources.subprocess_workaround import subprocess_setup
from debsources.tests.db_testing import DB_COMPARE_QUERIES, DbTestFixture
from debsources.tests.testdata import TEST_DATA_DIR
from debsources.tests.updater_testing import mk_conf


def compare_dirs(dir1, dir2, exclude=[]):
    """recursively compare dir1 with dir2

    return (True, None) if they are the same or a (False, diff) where diff is a
    textual list of files that differ (as per "diff --brief")

    """
    try:
        subprocess.check_output(
            ["diff", "-Naur", "--brief"]
            + ["--exclude=" + pat for pat in exclude]
            + [dir1, dir2],
            preexec_fn=subprocess_setup,
        )
        return True, None
    except subprocess.CalledProcessError as e:
        return False, e.output


def compare_files(file1, file2):
    """compare file1 and file2 with diff

    return (True, None) if they are the same or a (False, diff) where diff is a
    textual diff between the two (as per "diff -u")

    """
    try:
        subprocess.check_output(
            ["diff", "-Nu", file1, file2], preexec_fn=subprocess_setup
        )
        return True, None
    except subprocess.CalledProcessError as e:
        return False, e.output


def db_mv_tables_to_schema(session, new_schema):
    """move all debsources tables from the 'public' schema to new_schema

    then recreate the corresponding (empty) tables under 'public'
    """
    session.execute("CREATE SCHEMA %s" % new_schema)
    for tblname, table in models.Base.metadata.tables.items():
        session.execute("ALTER TABLE %s SET SCHEMA %s" % (tblname, new_schema))
        session.execute(sqlalchemy.schema.CreateTable(table))


def assert_db_schema_equal(test_subj, expected_schema, actual_schema):
    for tbl, q in DB_COMPARE_QUERIES.items():
        expected = test_subj.session.execute(
            q % {"schema": expected_schema}
        ).fetchmany()
        actual = test_subj.session.execute(q % {"schema": actual_schema}).fetchmany()
        test_subj.assertSequenceEqual(
            expected, actual, msg="table %s differs from reference" % tbl
        )


def assert_dir_equal(test_subj, dir1, dir2, exclude=[]):
    dir_eq, dir_diff = compare_dirs(dir1, dir2, exclude)
    if not dir_eq:
        print(dir_diff)
    test_subj.assertTrue(dir_eq, "file system storages differ")


@attr("infra")
@attr("postgres")
@attr("slow")
class Updater(unittest.TestCase, DbTestFixture):
    def setUp(self):
        self.db_setup()
        self.tmpdir = Path(tempfile.mkdtemp(suffix=".debsources-test"))
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
        obs, exts = mainlib.load_hooks(self.conf)
        self.conf["observers"], self.conf["file_exts"] = obs, exts
        updater.update(self.conf, self.session, stages)

    @istest
    def producesReferenceDb(self):
        db_mv_tables_to_schema(self.session, "ref")
        self.do_update()

        # sources/ dir comparison. Ignored patterns:
        # - plugin result caches -> because most of them are in os.walk()
        #   order, which is not stable
        # - dpkg-source log stored in *.log
        exclude_pat = ["*" + ext for ext in self.conf["file_exts"]] + ["*.log"]
        assert_dir_equal(
            self,
            self.tmpdir / "sources",
            TEST_DATA_DIR / "sources",
            exclude=exclude_pat,
        )

        assert_db_schema_equal(self, "ref", "public")

    @istest
    def producesReferenceSourcesTxt(self):
        def parse_sources_txt(fname):
            with open(fname) as f:
                for line in f:
                    fields = line.split()
                    if fields[3].startswith("/"):
                        fields[3] = str(
                            Path(fields[3]).relative_to(self.conf["mirror_dir"])
                        )
                    if fields[4].startswith("/"):
                        fields[4] = str(
                            Path(fields[4]).relative_to(self.conf["mirror_dir"])
                        )
                    yield fields

        # given DB is pre-filled, this should be a "do-almost-nothing" update
        self.do_update()
        srctxt_path = Path("cache") / "sources.txt"
        # Entries need to be sorted for comparison, since no order is guaranteed
        actual_srctxt = sorted(list(parse_sources_txt(self.tmpdir / srctxt_path)))
        expected_srctxt = sorted(list(parse_sources_txt(TEST_DATA_DIR / srctxt_path)))
        self.assertSequenceEqual(actual_srctxt, expected_srctxt)

    @istest
    def recreatesDbFromFiles(self):
        orig_sources = TEST_DATA_DIR / "sources"
        dest_sources = self.tmpdir / "sources"
        shutil.copytree(orig_sources, dest_sources)
        db_mv_tables_to_schema(self.session, "ref")

        self.conf["backends"] = set(["db", "hooks", "hooks.db"])
        self.do_update()

        # check that the update didn't touch filesystem storage
        assert_dir_equal(self, orig_sources, dest_sources)
        # check that the update recreate an identical DB
        assert_db_schema_equal(self, "ref", "public")

    @istest
    def garbageCollects(self):
        GC_PACKAGE = ("ocaml-curses", "1.0.3-1")
        PKG_SUITE = "squeeze"
        PKG_AREA = "main"

        # make fresh copies of sources/ and mirror dir
        orig_sources = TEST_DATA_DIR / "sources"
        orig_mirror = TEST_DATA_DIR / "mirror"
        new_sources = self.tmpdir / "sources2"
        new_mirror = self.tmpdir / "mirror2"
        shutil.copytree(orig_sources, new_sources)
        shutil.copytree(orig_mirror, new_mirror)
        self.conf["mirror_dir"] = new_mirror
        self.conf["sources_dir"] = new_sources

        pkgdir = (
            new_sources / PKG_AREA / GC_PACKAGE[0][0] / GC_PACKAGE[0] / GC_PACKAGE[1]
        )
        src_index = (
            new_mirror / "dists" / PKG_SUITE / PKG_AREA / "source" / "Sources.gz"
        )

        # rm package to be GC'd from mirror (actually, remove everything...)
        with open(src_index, "w") as f:
            f.truncate()

        # update run that should not GC, due to timestamp
        os.utime(pkgdir, None)
        self.conf["expire_days"] = 3
        self.do_update()
        self.assertTrue(
            pkgdir.exists(),
            "young gone package %s/%s disappeared from FS storage" % GC_PACKAGE,
        )
        self.assertTrue(
            db_storage.lookup_package(self.session, *GC_PACKAGE),
            "young gone package %s/%s disappeared from DB storage" % GC_PACKAGE,
        )

        # another update run without grace period, package should go
        self.conf["expire_days"] = 0
        self.do_update()
        self.assertFalse(
            pkgdir.exists(), "gone package %s/%s persisted in FS storage" % GC_PACKAGE
        )
        self.assertFalse(
            db_storage.lookup_package(self.session, *GC_PACKAGE),
            "gone package %s/%s persisted in DB storage" % GC_PACKAGE,
        )

    @istest
    def excludeFiles(self):
        PKG = "bsdgames-nonfree"
        PKG_PREFIX = PKG[0]
        EXCLUDED_GLOB = "tests/battlestar.in17"
        EXCLUSIONS = """Explanation: test case
Package: %s
Files: %s
Action: remove""" % (
            PKG,
            EXCLUDED_GLOB,
        )
        excluded_paths = (
            self.tmpdir / "sources" / "*" / PKG_PREFIX / PKG / "*" / EXCLUDED_GLOB
        )

        # dummy update run, copying over sources/ dir
        orig_sources = TEST_DATA_DIR / "sources"
        dest_sources = self.tmpdir / "sources"
        shutil.copytree(orig_sources, dest_sources)
        self.do_update()
        self.assertTrue(glob.glob(str(excluded_paths)))

        # second update run, this time with exclusions
        exclude_tmp = self.tmpdir / "exclude.conf"
        with open(exclude_tmp, "w") as f:
            f.write(EXCLUSIONS)
        self.conf["exclude"] = mainlib.parse_exclude(exclude_tmp)
        pkgs = (
            self.session.query(models.Package)
            .join(models.PackageName)
            .filter_by(name=PKG)
        )
        for pkg in pkgs:
            self.session.delete(pkg)
        self.do_update()
        self.assertFalse(glob.glob(str(excluded_paths)))


@attr("infra")
@attr("cache")
@attr("metadata")
@attr("slow")
class MetadataCache(unittest.TestCase, DbTestFixture):
    """tests for on-disk cache of debsources metadata

    usually stored in cache/stats.data

    """

    def setUp(self):
        self.db_setup()
        self.tmpdir = Path(tempfile.mkdtemp(suffix=".debsources-test"))
        self.conf = mk_conf(self.tmpdir)
        dummy_status = updater.UpdateStatus()

        updater.update_statistics(dummy_status, self.conf, self.session)

        stats_data = self.conf["cache_dir"] / "stats.data"
        self.stats = statistics.load_metadata_cache(stats_data)

    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)

    @istest
    def sizeMatchesReferenceDb(self):
        EXPECTED_SIZE = 181628
        self.assertEqual(EXPECTED_SIZE, self.stats["total.disk_usage"])

    @istest
    def statsMatchReferenceDb(self):
        expected_stats = {  # just a few samples
            "total.ctags": 116833,
            "debian_sid.ctags": 28723,
            "debian_squeeze.ctags": 31015,
            "debian_experimental.disk_usage": 12964,
            "total.source_files": 9354,
            "debian_experimental.source_files": 1396,
            "debian_jessie.source_files": 2059,
            "total.source_packages": 37,
            "debian_squeeze.source_packages": 13,
            "debian_wheezy.source_packages": 12,
            "debian_sid.sloccount.awk": 25,
            "debian_sid.sloccount.cpp": 41458,
            "debian_squeeze.sloccount.cpp": 36508,
            "debian_wheezy.sloccount.cpp": 37375,
            "total.sloccount.perl": 4325,
            "total.sloccount.python": 9193,
            "debian_wheezy.sloccount.python": 2798,
            "debian_squeeze.sloccount.ruby": 193,
            "debian_wheezy.sloccount.ruby": 193,
            "total.sloccount": 1250903,
            "total.sloccount.javascript": 212,
            "debian_squeeze.sloccount": 315750,
        }
        self.assertDictContainsSubset(expected_stats, self.stats)

    @istest
    def licenseStatsMatchReferenceDb(self):
        license_stats_data = self.conf["cache_dir"] / "license_stats.data"
        license_stats = statistics.load_metadata_cache(license_stats_data)
        expected_stats = {  # just a few samples
            "experimental.LGPL-2.1+": 749,
            "experimental.unknown": 4,
            "jessie.GPL-2": 31,
            "overall.LGPL-2.1+": 749,
            "sid.GPL-3+": 533,
            "sid.GPL-2": 31,
            "wheezy.GPL-2": 30,
            "wheezy.GPL-2+": 58,
        }

        self.assertDictContainsSubset(expected_stats, license_stats)
