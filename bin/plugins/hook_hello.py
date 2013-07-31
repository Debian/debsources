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

import logging

def add_package(session, pkg, pkgdir):
    logging.info('add-package %s %s' % (pkg, pkgdir))

def rm_package(session, pkg, pkgdir):
    logging.info('rm-package %s %s' % (pkg, pkgdir))

def debsources_main(debsources):
    logging.info('subscribe to: add-package, rm_package')
    debsources['subscribe']('add-package', add_package, title='hello')
    debsources['subscribe']('rm-package', rm_package, title='hello')
