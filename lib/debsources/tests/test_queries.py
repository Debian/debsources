# Copyright (C) 2014-2015  The Debsources developers
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
from pathlib import Path

from nose.plugins.attrib import attr

import debsources.query as qry
from debsources.app.app_factory import AppWrapper
from debsources.tests.db_testing import DbTestFixture
from debsources.tests.testdata import TEST_DB_NAME


@attr("Queries")
class QueriesTest(unittest.TestCase, DbTestFixture):
    @classmethod
    def setUpClass(cls):
        cls.db_setup_cls()

        app_wrapper = AppWrapper()

        # erases a few configuration parameters needed for testing:
        uri = "postgresql:///" + TEST_DB_NAME
        app_wrapper.app.config["DB_URI"] = uri
        app_wrapper.app.config["LIST_OFFSET"] = 5
        app_wrapper.app.testing = True

        app_wrapper.go()

        cls.app = app_wrapper.app.test_client()
        cls.app_wrapper = app_wrapper

    @classmethod
    def tearDownClass(cls):
        cls.app_wrapper.app.engine.dispose()
        cls.db_teardown_cls()

    def test_packages_prefixes(self):
        self.assertEqual(
            qry.pkg_names_get_packages_prefixes(
                self.app_wrapper.app.config["CACHE_DIR"]
            ),
            ["a", "b", "c", "d", "f", "g", "l", "libc", "m", "n", "o", "p", "s", "u"],
        )

    def test_list_versions(self):
        # Test without suit
        packages = qry.pkg_names_list_versions(self.session, "gnubg")
        self.assertEqual(
            [p.version for p in packages],
            ["0.90+20091206-4", "0.90+20120429-1", "1.02.000-2"],
        )

        # Test with suit
        packages = qry.pkg_names_list_versions(self.session, "gnubg", "wheezy")
        self.assertEqual([p.version for p in packages], ["0.90+20120429-1"])

        # Test when suit_order is given as parameter
        packages = qry.pkg_names_list_versions(
            self.session, "gnubg", suite_order=["squeeze", "jessie", "sid", "wheezy"]
        )
        self.assertEqual(
            [p.version for p in packages],
            ["0.90+20091206-4", "1.02.000-2", "0.90+20120429-1"],
        )

        packages = qry.pkg_names_list_versions(
            self.session, "gnubg", suite_order=["squeeze", "wheezy", "jessie", "sid"]
        )
        self.assertEqual(
            [p.version for p in packages],
            ["0.90+20091206-4", "0.90+20120429-1", "1.02.000-2"],
        )

        # Test returning suites without suit as parameter
        self.assertTrue(
            {"suites": ["wheezy"], "version": "0.90+20120429-1", "area": "main"}
            in qry.pkg_names_list_versions_w_suites(self.session, "gnubg")
        )

        # Test returning suites with a suit as parameter
        self.assertEqual(
            qry.pkg_names_list_versions_w_suites(self.session, "gnubg", "jessie"),
            [
                {
                    "suites": ["jessie", "sid"],
                    "version": "1.02.000-2",
                    "area": "main",
                }
            ],
        )

    def test_find_ctag(self):
        self.assertEqual(qry.find_ctag(self.session, "swap")[0], 8)

        ctags = qry.find_ctag(self.session, "swap", "gnubg")
        self.assertEqual(ctags[0], 5)
        self.assertTrue(
            {
                "path": Path("eval.c"),
                "line": 1747,
                "version": "0.90+20091206-4",
                "package": "gnubg",
            }
            in ctags[1]
        )

    def test_ratio(self):
        # overall
        self.assertEqual(qry.get_ratio(self.session), 77)
        # per suite
        self.assertEqual(qry.get_ratio(self.session, "jessie"), 51)
        self.assertEqual(qry.get_ratio(self.session, "squeeze"), 100)
