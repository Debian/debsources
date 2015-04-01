# Copyright (C) 2013-2015  The Debsources developers <info@sources.debian.net>.
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

import unittest

from nose.tools import istest
from nose.plugins.attrib import attr

from debsources.filetype import get_filetype, get_highlightjs_language
from debsources.filetype import HTML, PHP, PYTHON, RUBY, XML


@attr('filetype')
class FiletypeTests(unittest.TestCase):
    """ Unit tests for debsources.filetype """

    @istest
    def pythonShebang(self):
        self.assertEqual(get_filetype('foo', '#!/usr/bin/python'), PYTHON)

    @istest
    def envPythonShebang(self):
        self.assertEqual(get_filetype('foo', '#!/usr/bin/env python'), PYTHON)

    @istest
    def envRubyShebang(self):
        self.assertEqual(get_filetype('foo', '#!/usr/bin/env ruby'), RUBY)

    @istest
    def testUnknownShebang(self):
        self.assertIsNone(get_filetype('foo', '#!/usr/bin/foobar'))

    @istest
    def pythonExtension(self):
        self.assertEqual(get_filetype('foo.py', 'foobar'), PYTHON)

    @istest
    def rubyExtension(self):
        self.assertEqual(get_filetype('foo.rb', 'foobar'), RUBY)

    @istest
    def unknownExtension(self):
        self.assertIsNone(get_filetype('foo.bar', 'foobar'))

    @istest
    def htmlTag(self):
        self.assertEqual(get_filetype('foo', '<html><head>'), HTML)

    @istest
    def xmlTag(self):
        self.assertEqual(get_filetype('foo', '<?xml>'), XML)

    @istest
    def phpTag(self):
        self.assertEqual(get_filetype('foo', "<?php echo('hello') ?>"), PHP)

    @istest
    def hilightjsLanguageDjango(self):
        self.assertEqual(get_highlightjs_language("foo.html", "foobar", None),
                         "django")

    @istest
    def hilightjsLanguagePerl(self):
        self.assertEqual(get_highlightjs_language("foo",
                                                  "#!/bin/perl\n",
                                                  None),
                         "perl")
