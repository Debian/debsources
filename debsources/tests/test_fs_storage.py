# Copyright (C) 2015  The Debsources developers <info@sources.debian.net>.
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

import os.path
import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

from debsources.fs_storage import parse_path, walk
from debsources.tests.testdata import *  # NOQA


def make_path(path):
    return os.path.join(TEST_DATA_DIR, 'sources', path)


@attr('fs_storage')
class FsStorageTests(unittest.TestCase):
    """ Unit tests for debsources.fs_storage """

    @istest
    def assertWalkLength(self):
        self.assertEqual(len([f for f in walk(make_path(''))]),
                         288)

    @istest
    def assertWalkTestChecksums(self):
        self.assertEqual(
            len([f for f in walk(make_path(''),
                                 test=lambda x: 'checksums' in x)]),
            36)

    @istest
    def parsePathDir(self):
        self.assertDictEqual(
            parse_path(make_path('main/libc/libcaca/0.99.beta17-1')),
            {
                'package': 'libcaca',
                'version': '0.99.beta17-1',
                'ext': None,
            })

    @istest
    def parsePathChecksums(self):
        self.assertDictEqual(
            parse_path(make_path('main/libc/libcaca/0.99.beta17-1.checksums')),
            {
                'package': 'libcaca',
                'version': '0.99.beta17-1',
                'ext': '.checksums',
            })
