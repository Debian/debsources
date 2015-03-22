# Copyright (C) 2013-2014  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import

import logging

conf = None


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('add-package %s %s' % (pkg, pkgdir))


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('rm-package %s %s' % (pkg, pkgdir))


def init_plugin(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title='hello')
    debsources['subscribe']('rm-package', rm_package, title='hello')
