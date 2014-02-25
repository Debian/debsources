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

import statistics

from db_testing import DbTestFixture, pg_dump


@attr('infra')
class Stats(unittest.TestCase, DbTestFixture):

    def setUp(self):
        self.db_setup()
        self.maxDiff = None

    def tearDown(self):
        self.db_teardown()

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
