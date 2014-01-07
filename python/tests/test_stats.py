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

import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

import statistics

from dbhelpers import DbTestFixture, pg_dump


@attr('infra')
class Stats(unittest.TestCase, DbTestFixture):


    def setUp(self):
        self.db_setup()


    def tearDown(self):
        self.db_teardown()


    @istest
    def sizeTotalsMatchReferenceDb(self):
        sizes = {
            'squeeze': 44316,
            'wheezy': 39688,
            'jessie': 43032,
            'sid': 43032,
            'experimental': 6520,
        }
        total_size = 122628
        for suite, size in sizes.iteritems():
            self.assertEqual(size, statistics.size(self.session, suite=suite))
        self.assertEqual(total_size, statistics.size(self.session))


    @istest
    def slocTotalsMatchReferenceDb(self):
        slocs_jessie = {
            'ansic': 140353,
            'asm': 65,
            'awk': 25,
            'cpp': 41458,
            'cs': 1213,
            'java': 916,
            'lex': 223,
            'lisp': 2167,
            'ml': 5044,
            'objc': 836,
            'perl': 64,
            'python': 2916,
            'ruby': 193,
            'sh': 25022,
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
