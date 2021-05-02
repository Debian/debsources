# Copyright (C) 2013-2015  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

from debsources import statistics

from debsources.tests.db_testing import DbTestFixture


@attr("infra")
class Stats(unittest.TestCase, DbTestFixture):
    @classmethod
    def setUpClass(cls):
        cls.db_setup_cls()

    @classmethod
    def tearDownClass(cls):
        cls.db_teardown_cls()

    def setUp(self):
        self.maxDiff = None

    def assertSuiteCountsEqual(self, expected, query_method):
        for suite, expected_count in expected.items():
            actual_count = query_method(self.session, suite=suite)
            self.assertEqual(
                expected_count,
                actual_count,
                "%d != %d for suite %s" % (expected_count, actual_count, suite),
            )

    @istest
    def diskUsagesMatchReferenceDb(self):
        sizes = {
            "squeeze": 44316,
            "wheezy": 39688,
            "jessie": 51428,
            "sid": 54456,
            "experimental": 12964,
        }
        total_size = 181628
        self.assertSuiteCountsEqual(sizes, statistics.disk_usage)
        self.assertEqual(total_size, statistics.disk_usage(self.session))

    @istest
    def sourcePackagesCountsMatchReferenceDb(self):
        source_packages = {
            "squeeze": 13,
            "wheezy": 12,
            "jessie": 14,
            "sid": 14,
            "experimental": 2,
        }
        total_source_packages = 37
        self.assertSuiteCountsEqual(source_packages, statistics.source_packages)
        self.assertEqual(
            total_source_packages, statistics.source_packages(self.session)
        )

    @istest
    def sourceFilesCountsMatchReferenceDb(self):
        source_files = {
            "squeeze": 2024,
            "wheezy": 1632,
            "jessie": 2059,
            "sid": 2613,
            "experimental": 1396,
        }
        total_files = 9354
        self.assertSuiteCountsEqual(source_files, statistics.source_files)
        self.assertEqual(total_files, statistics.source_files(self.session))

    @istest
    def slocCountsMatchReferenceDb(self):
        slocs_jessie = {
            "ansic": 166724,
            "asm": 65,
            "awk": 25,
            "cpp": 41458,
            "cs": 1213,
            "java": 916,
            "lex": 223,
            "lisp": 2193,
            "makefile": 2104,
            "ml": 5044,
            "objc": 836,
            "perl": 1199,
            "python": 2916,
            "ruby": 193,
            "sed": 16,
            "sh": 30045,
            "sql": 237,
            "xml": 14932,
            "yacc": 312,
        }
        slocs_python = 9193
        slocs_cpp_exp = 87521
        self.assertEqual(
            slocs_jessie, statistics.sloccount_summary(self.session, suite="jessie")
        )
        self.assertEqual(
            slocs_python, statistics.sloccount_lang(self.session, "python")
        )
        self.assertEqual(
            slocs_cpp_exp,
            statistics.sloccount_lang(self.session, "cpp", suite="experimental"),
        )

    @istest
    def ctagsCountsMatchReferenceDb(self):
        ctags = {
            "squeeze": 31015,
            "wheezy": 20521,
            "jessie": 23816,
            "sid": 28723,
            "experimental": 17284,
        }
        total_ctags = 116833
        self.assertSuiteCountsEqual(ctags, statistics.ctags)
        self.assertEqual(total_ctags, statistics.ctags(self.session))

    @istest
    def slocPerPkgMatchReferenceDb(self):
        LARGEST = ("cvsnt", "2.5.03.2382-3", 293583)
        SMALLEST = ("susv3", "6.1", 10)
        LARGEST_exp = ("beignet", "1.0.0-1", 81413)
        SMALLEST_exp = ("ledger", "3.0.0~20130313+b608ed2-1", 46060)

        slocs_all = statistics.sloc_per_package(self.session)
        self.assertEqual(slocs_all[0], LARGEST)
        self.assertEqual(slocs_all[-1], SMALLEST)

        slocs_exp = statistics.sloc_per_package(self.session, suite="experimental")
        self.assertEqual(slocs_exp[0], LARGEST_exp)
        self.assertEqual(slocs_exp[-1], SMALLEST_exp)

    @istest
    def areaFiltersMatchReferenceDb(self):
        self.assertEqual(statistics.disk_usage(self.session), 181628)
        self.assertEqual(statistics.disk_usage(self.session, areas=["main"]), 156072)
        self.assertEqual(
            statistics.disk_usage(self.session, suite="wheezy", areas=["main"]), 35824
        )

        area_count = statistics.source_packages(self.session, areas=["main"])
        self.assertEqual(area_count, 18)
        self.assertLessEqual(area_count, statistics.source_packages(self.session))

        area_count = statistics.source_files(self.session, areas=["contrib"])
        self.assertEqual(area_count, 372)
        self.assertLessEqual(area_count, statistics.source_files(self.session))

        area_count = statistics.sloccount_lang(
            self.session, "ansic", areas=["non-free"]
        )
        self.assertEqual(area_count, 147526)
        self.assertLessEqual(
            area_count, statistics.sloccount_lang(self.session, "ansic")
        )

        area_count = statistics.ctags(self.session, areas=["main"])
        self.assertEqual(area_count, 88251)
        self.assertLessEqual(area_count, statistics.ctags(self.session))

    @istest
    def test_license_summary(self):
        expected_stats = {"BSD-3-clause": 1, "GFDL-1.3+": 6, "GPL-2": 31, "GPL-2+": 105}

        jessie_stats = statistics.licenses_summary(
            dict(statistics.get_licenses(self.session, "jessie"))
        )
        self.assertDictContainsSubset(expected_stats, jessie_stats)

    @istest
    def test_group_by_stats(self):
        stats = dict(statistics.stats_grouped_by(self.session, "disk_usage"))
        self.assertEqual(stats["etch"], 32736)

        stats = dict(statistics.stats_grouped_by(self.session, "ctags"))
        self.assertEqual(stats["wheezy"], 20521)

        stats = dict(statistics.stats_grouped_by(self.session, "source_packages"))
        self.assertEqual(stats["jessie"], 14)

        stats = dict(statistics.stats_grouped_by(self.session, "source_files"))
        self.assertEqual(stats["wheezy"], 1632)

        sloc_list = statistics.stats_grouped_by(self.session, "sloccount")
        wheezy_sloc = [[item[1], item[2]] for item in sloc_list if item[0] == "wheezy"]
        self.assertEqual(dict(wheezy_sloc)["sh"], 13560)
