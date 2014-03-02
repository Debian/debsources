# Copyright (C) 2014  Stefano Zacchiroli <zack@upsilon.cc>
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
import tempfile
import unittest

from nose.tools import istest, nottest
from nose.plugins.attrib import attr

import archiver
import dbutils
import debmirror
import mainlib
import models
import updater

from db_testing import DbTestFixture, pg_dump, DB_COMPARE_QUERIES
from updater_testing import mk_conf
from testdata import *


@attr('infra')
@attr('postgres')
class Archiver(unittest.TestCase, DbTestFixture):

    def setUp(self):
        self.db_setup()
        self.tmpdir = tempfile.mkdtemp(suffix='.debsources-test')
        self.conf = mk_conf(self.tmpdir)
        self.longMessage = True
        self.maxDiff = None

        orig_sources = os.path.join(TEST_DATA_DIR, 'sources')
        dest_sources = self.conf['sources_dir']
        shutil.copytree(orig_sources, dest_sources)

        mainlib.init_logging(self.conf, console_verbosity=logging.WARNING)
        obs, exts = mainlib.load_hooks(self.conf)
        self.conf['observers'], self.conf['file_exts'] = obs, exts

        self.archive = debmirror.SourceMirrorArchive(self.conf['mirror_archive_dir'])


    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)


    def assertHasPackage(self, package, version):
        v = dbutils.lookup_version(self.session, package, version)
        self.assertIsNotNone(v, msg='missing package %s/%s' % (package, version))
        return v

    def assertHasLivePackage(self, package, version):
        v = self.assertHasPackage(package, version)
        self.assertFalse(v.sticky, msg='unexpected sticky bit on package %s/%s'
                        % (package, version))
    def assertHasStickyPackage(self, package, version):
        v = self.assertHasPackage(package, version)
        self.assertTrue(v.sticky, msg='missing sticky bit on package %s/%s'
                        % (package, version))

    def assertLacksStickyPackage(self, package, version):
        v = dbutils.lookup_version(self.session, package, version)
        self.assertIsNone(v, msg='missing sticky package %s/%s'
                          % (package, version))

    def assertHasStickySuite(self, suite):
        s = archiver._lookup_db_suite(self.session, suite)
        self.assertIsNotNone(s, msg='missing sticky suite ' + suite)

    def assertLacksStickySuite(self, suite):
        s = archiver._lookup_db_suite(self.session, suite)
        self.assertIsNone(s, msg='present sticky suite ' + suite)


    @istest
    @attr('slow')
    def addsStickySuite(self):
        HAMM_PACKAGES = [ ('3dchess', '0.8.1-3'), ('ed', '0.2-16') ]

        archiver.add_suite(self.conf, self.session, 'hamm', self.archive)

        self.assertHasStickySuite('hamm')
        for pkg in HAMM_PACKAGES:
            self.assertHasStickyPackage(*pkg)


    @istest
    @attr('slow')
    def removesStickySuite(self):
        SARGE_PACKAGES = [ ('asm', '1.5.2-1'), ('zziplib', '0.12.83-4') ]

        archiver.add_suite(self.conf, self.session, 'sarge', self.archive)
        self.assertHasStickySuite('sarge')
        for pkg in SARGE_PACKAGES:
            self.assertHasStickyPackage(*pkg)

        archiver.remove_suite(self.conf, self.session, 'sarge')
        self.assertLacksStickySuite('sarge')
        for pkg in SARGE_PACKAGES:
            self.assertLacksStickyPackage(*pkg)


    @istest
    @attr('slow')
    def countsReferences(self):
        DUP_PKG = ('2utf', '1.04')	# in both hamm and slink

        archiver.add_suite(self.conf, self.session, 'hamm', self.archive)
        self.assertHasStickyPackage(*DUP_PKG)

        archiver.add_suite(self.conf, self.session, 'slink', self.archive)
        self.assertHasStickyPackage(*DUP_PKG)

        archiver.remove_suite(self.conf, self.session, 'hamm')
        self.assertHasStickyPackage(*DUP_PKG)

        archiver.remove_suite(self.conf, self.session, 'slink')
        self.assertLacksStickyPackage(*DUP_PKG)


    @istest
    @attr('slow')
    def stayClearOfLiveSuites(self):
        DUP_PKG = ('libcaca', '0.99.beta17-1')	# in both lenny (sticky) and squeeze (live)
        self.assertHasLivePackage(*DUP_PKG)

        archiver.add_suite(self.conf, self.session, 'lenny', self.archive)
        self.assertHasStickyPackage(*DUP_PKG)

        archiver.remove_suite(self.conf, self.session, 'lenny')
        self.assertHasLivePackage(*DUP_PKG)


    @istest
    @attr('slow')
    def guessAreaForSectionlessPkgs(self):
        sectionless_pkg = ('tripwire', '1.2-15')

        archiver.add_suite(self.conf, self.session, 'slink', self.archive)
        v = dbutils.lookup_version(self.session, *sectionless_pkg)
        self.assertEqual('non-free', v.area)


    @istest
    @attr('slow')
    def canAddPkgsWSpecialFiles(self):
        pkg_w_pipe = ('freewrl', '0.20.a1-3')

        archiver.add_suite(self.conf, self.session, 'potato', self.archive)
        self.assertHasStickyPackage(*pkg_w_pipe)
