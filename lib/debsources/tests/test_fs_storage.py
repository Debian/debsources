# Copyright (C) 2015-2021  The Debsources developers
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


import unittest

from nose.plugins.attrib import attr
from nose.tools import istest

from debsources.fs_storage import parse_path, walk
from debsources.tests.testdata import TEST_DATA_DIR


def make_path(path):
    return TEST_DATA_DIR / "sources" / path


@attr("fs_storage")
class FsStorageTests(unittest.TestCase):
    """Unit tests for debsources.fs_storage"""

    @istest
    def assertWalkLength(self):
        self.assertEqual(len([f for f in walk(make_path(""))]), 268)

    @istest
    def assertWalkTestChecksums(self):
        self.assertEqual(
            len([f for f in walk(make_path(""), test=lambda x: "checksums" in str(x))]),
            37,
        )

    @istest
    def parsePathDir(self):
        self.assertDictEqual(
            parse_path(make_path("main/libc/libcaca/0.99.beta17-1")),
            {
                "package": "libcaca",
                "version": "0.99.beta17-1",
                "ext": None,
            },
        )

    @istest
    def parsePathChecksums(self):
        self.assertDictEqual(
            parse_path(make_path("main/libc/libcaca/0.99.beta17-1.checksums")),
            {
                "package": "libcaca",
                "version": "0.99.beta17-1",
                "ext": ".checksums",
            },
        )
