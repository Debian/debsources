# Copyright (C) 2022-2022  The Debsources developers
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

"""Test Flask FilePathConverter."""

import unittest

from debsources.app.file_path_converter import FilePathConverter


class FilePathConverterTestCase(unittest.TestCase):
    """Test FilePathConverter."""

    def test_to_python(self):
        scenarios = [
            ("somepath", "somepath"),
            ("some%2Bpath", "some+path"),
            ("some+path", "some+path"),
            ("some%2Bother%EDpath", "some+other\udcedpath"),
        ]

        for scenario in scenarios:
            self.assertEqual(
                FilePathConverter.to_python(None, scenario[0]), scenario[1]
            )

    def test_to_url(self):
        scenarios = [
            ("somepath", "somepath"),
            ("some+path", "some%2Bpath"),
            ("some+other\udcedpath", "some%2Bother%25EDpath"),
        ]

        for scenario in scenarios:
            self.assertEqual(FilePathConverter.to_url(None, scenario[0]), scenario[1])
