# Copyright (C) 2014  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

from __future__ import absolute_import

import logging
import os
import shutil
import tempfile
import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

from debsources import archiver
from debsources import db_storage
from debsources import debmirror
from debsources import mainlib
from debsources import statistics
from debsources import updater

from debsources.consts import DEBIAN_RELEASES
from debsources.tests.db_testing import DbTestFixture
from debsources.tests.updater_testing import mk_conf
from debsources.tests.testdata import TEST_DATA_DIR


@attr('infra')
@attr('postgres')
class Archiver(unittest.TestCase, DbTestFixture):

    TEST_STAGES = set([updater.STAGE_EXTRACT, updater.STAGE_SUITES,
                       updater.STAGE_GC])

    def setUp(self):
        self.db_setup()
        self.tmpdir = tempfile.mkdtemp(suffix='.debsources-test')
        self.conf = mk_conf(self.tmpdir)
        self.conf['stages'] = self.TEST_STAGES
        self.longMessage = True
        self.maxDiff = None

        orig_sources = os.path.join(TEST_DATA_DIR, 'sources')
        dest_sources = self.conf['sources_dir']
        shutil.copytree(orig_sources, dest_sources)

        mainlib.init_logging(self.conf, console_verbosity=logging.WARNING)
        obs, exts = mainlib.load_hooks(self.conf)
        self.conf['observers'], self.conf['file_exts'] = obs, exts

        self.archive = debmirror.SourceMirrorArchive(
            self.conf['mirror_archive_dir'])

    def tearDown(self):
        self.db_teardown()
        shutil.rmtree(self.tmpdir)

    def assertHasPackage(self, package, version):
        p = db_storage.lookup_package(self.session, package, version)
        self.assertIsNotNone(p, msg='missing package %s/%s' %
                             (package, version))
        return p

    def assertHasLivePackage(self, package, version):
        p = self.assertHasPackage(package, version)
        self.assertFalse(p.sticky, msg='unexpected sticky bit on package %s/%s'
                         % (package, version))

    def assertHasStickyPackage(self, package, version):
        p = self.assertHasPackage(package, version)
        self.assertTrue(p.sticky, msg='missing sticky bit on package %s/%s'
                        % (package, version))

    def assertLacksStickyPackage(self, package, version):
        p = db_storage.lookup_package(self.session, package, version)
        self.assertIsNone(p, msg='missing sticky package %s/%s'
                          % (package, version))

    def assertHasStickySuite(self, suite):
        s = db_storage.lookup_db_suite(self.session, suite, sticky=True)
        self.assertIsNotNone(s, msg='missing sticky suite ' + suite)

    def assertLacksStickySuite(self, suite):
        s = db_storage.lookup_db_suite(self.session, suite, sticky=True)
        self.assertIsNone(s, msg='present sticky suite ' + suite)

    @istest
    @attr('slow')
    def addsStickySuites(self):
        SUITES = ['hamm', 'slink']
        PACKAGES = [('3dchess', '0.8.1-3'),  # hamm
                    ('ed', '0.2-16'),        # hamm
                    ('WMRack', '1.0b3-1')]   # slink, pkg w/ weird naming

        for suite in SUITES:
            archiver.add_suite(self.conf, self.session, suite, self.archive)

        for suite in SUITES:
            self.assertHasStickySuite(suite)
            s = db_storage.lookup_db_suite(self.session, suite, sticky=True)
            rel_info = DEBIAN_RELEASES[suite]
            self.assertEqual(s.version, rel_info['version'])
            self.assertEqual(s.release_date, rel_info['date'])

        for pkg in PACKAGES:
            self.assertHasStickyPackage(*pkg)

    @istest
    @attr('slow')
    def removesStickySuite(self):
        SARGE_PACKAGES = [('asm', '1.5.2-1'), ('zziplib', '0.12.83-4')]
        stats_file = os.path.join(self.conf['cache_dir'], 'stats.data')

        # to test stats.data cleanup
        self.conf['stages'] = self.TEST_STAGES.union(
            set([updater.STAGE_STATS]))
        archiver.add_suite(self.conf, self.session, 'sarge', self.archive)
        self.assertHasStickySuite('sarge')
        for pkg in SARGE_PACKAGES:
            self.assertHasStickyPackage(*pkg)
        stats = statistics.load_metadata_cache(stats_file)
        self.assertTrue('debian_sarge.sloccount' in stats)

        archiver.remove_suite(self.conf, self.session, 'sarge')
        self.assertLacksStickySuite('sarge')
        for pkg in SARGE_PACKAGES:
            self.assertLacksStickyPackage(*pkg)
        stats = statistics.load_metadata_cache(stats_file)
        self.assertFalse('debian_sarge.sloccount' in stats)

    @istest
    @attr('slow')
    def countsReferences(self):
        DUP_PKG = ('2utf', '1.04')  # in both hamm and slink

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
        # in both lenny (sticky) and squeeze (live)
        DUP_PKG = ('libcaca', '0.99.beta17-1')
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
        p = db_storage.lookup_package(self.session, *sectionless_pkg)
        self.assertEqual('non-free', p.area)

    @istest
    @attr('slow')
    def canAddPkgsWSpecialFiles(self):
        pkg_w_pipe = ('freewrl', '0.20.a1-3')

        archiver.add_suite(self.conf, self.session, 'potato', self.archive)
        self.assertHasStickyPackage(*pkg_w_pipe)
