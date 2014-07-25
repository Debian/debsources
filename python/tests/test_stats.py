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

import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

from debsources import statistics

from debsources.tests.db_testing import DbTestFixture, pg_dump


@attr('infra')
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
        for suite, expected_count in expected.iteritems():
            actual_count = query_method(self.session, suite=suite)
            self.assertEqual(expected_count, actual_count,
                             '%d != %d for suite %s' %
                             (expected_count, actual_count, suite))

    @istest
    def diskUsagesMatchReferenceDb(self):
        sizes = {
            'squeeze': 44316,
            'wheezy': 39688,
            'jessie': 43032,
            'sid': 43032,
            'experimental': 6520,
        }
        total_size = 122628
        self.assertSuiteCountsEqual(sizes, statistics.disk_usage)
        self.assertEqual(total_size, statistics.disk_usage(self.session))

    @istest
    def sourcePackagesCountsMatchReferenceDb(self):
        source_packages = {
            'squeeze': 13,
            'wheezy': 12,
            'jessie': 12,
            'sid': 12,
            'experimental': 1,
        }
        total_source_packages = 31
        self.assertSuiteCountsEqual(source_packages, statistics.source_packages)
        self.assertEqual(total_source_packages,
                         statistics.source_packages(self.session))

    @istest
    def sourceFilesCountsMatchReferenceDb(self):
        source_files = {
            'squeeze': 2024,
            'wheezy': 1632,
            'jessie': 1677,
            'sid': 1677,
            'experimental': 645,
        }
        total_files = 5489
        self.assertSuiteCountsEqual(source_files, statistics.source_files)
        self.assertEqual(total_files, statistics.source_files(self.session))

    @istest
    def slocCountsMatchReferenceDb(self):
        slocs_jessie = {
            'ansic': 140353,
            'asm': 65,
            'awk': 25,
            'cpp': 41458,
            'cs': 1213,
            'java': 916,
            'lex': 223,
            'lisp': 2167,
            'makefile': 1924,
            'ml': 5044,
            'objc': 836,
            'perl': 64,
            'python': 2916,
            'ruby': 193,
            'sh': 25022,
            'sql': 237,
            'xml': 14932,
            'yacc': 312,
        }
        slocs_python = 7760
        slocs_cpp_exp = 36755
        self.assertEqual(slocs_jessie,
                         statistics.sloccount_summary(self.session,
                                                      suite='jessie'))
        self.assertEqual(slocs_python,
                         statistics.sloccount_lang(self.session, 'python'))
        self.assertEqual(slocs_cpp_exp,
                         statistics.sloccount_lang(self.session, 'cpp',
                                              suite='experimental'))

    @istest
    def ctagsCountsMatchReferenceDb(self):
        ctags = {
            'squeeze': 30633,
            'wheezy': 20139,
            'jessie': 21395,
            'sid': 21395,
            'experimental': 4945,
        }
        total_ctags = 70166
        self.assertSuiteCountsEqual(ctags, statistics.ctags)
        self.assertEqual(total_ctags, statistics.ctags(self.session))


    @istest
    def slocPerPkgMatchReferenceDb(self):
        LARGEST = ('gnubg', '1.02.000-2', 124353)
        SMALLEST = ('susv3', '6.1', 10)
        LARGEST_exp = ('ledger', '3.0.0~20130313+b608ed2-1', 45848)
        SMALLEST_exp = LARGEST_exp

        slocs_all = statistics.sloc_per_package(self.session)
        self.assertEqual(slocs_all[0], LARGEST)
        self.assertEqual(slocs_all[-1], SMALLEST)

        slocs_exp = statistics.sloc_per_package(self.session,
                                                suite='experimental')
        self.assertEqual(slocs_exp[0], LARGEST_exp)
        self.assertEqual(slocs_exp[-1], SMALLEST_exp)


    @istest
    def areaFiltersMatchReferenceDb(self):
        self.assertEqual(statistics.disk_usage(self.session),
                         122628)
        self.assertEqual(statistics.disk_usage(self.session, areas=['main']),
                         104568)
        self.assertEqual(statistics.disk_usage(self.session, suite='wheezy', areas=['main']),
                         35824)

        area_count = statistics.source_packages(self.session, areas=['main'])
        self.assertEqual(area_count, 13)
        self.assertLessEqual(area_count, statistics.source_packages(self.session))

        area_count = statistics.source_files(self.session, areas=['contrib'])
        self.assertEqual(area_count, 372)
        self.assertLessEqual(area_count, statistics.source_files(self.session))

        area_count = statistics.sloccount_lang(self.session, 'ansic', areas=['non-free'])
        self.assertEqual(area_count, 121155)
        self.assertLessEqual(area_count, statistics.sloccount_lang(self.session, 'ansic'))

        area_count = statistics.ctags(self.session, areas=['main'])
        self.assertEqual(area_count, 43622)
        self.assertLessEqual(area_count, statistics.ctags(self.session))
