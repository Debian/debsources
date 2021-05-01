# Copyright (C) 2015  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING

from __future__ import absolute_import

import unittest
from pathlib import Path

from nose.tools import istest
from nose.plugins.attrib import attr

from debsources.hashutil import sha256sum
from debsources.tests.testdata import TEST_DATA_DIR


def make_path(path: Path) -> Path:
    return TEST_DATA_DIR / "sources" / path


@attr("hashutil")
class HashutilTests(unittest.TestCase):
    """ Unit tests for debsources.hashutil """

    @istest
    def assertSha256Sum(self):
        path = Path("main") / "libc" / "libcaca" / "0.99.beta18-1" / "COPYING"
        self.assertEqual(
            sha256sum(make_path(path)),
            "d10f0447c835a590ef137d99dd0e3ed29b5e032e7434a87315b30402bf14e7fd",
        )
