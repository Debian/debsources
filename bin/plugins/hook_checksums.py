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
import os

import dbutils
import hashutil

from models import Checksum


def walk_pkg_files(pkgdir):
    for root, dirs, files in os.walk(pkgdir):
        for file in files:
            yield os.path.join(root, file)


def add_package(session, pkg, pkgdir):
    logging.debug('add-package %s' % pkg)

    version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
    for path in walk_pkg_files(pkgdir):
        sha256 = hashutil.sha256sum(path)
        relpath = os.path.relpath(path, pkgdir)
        checksum = session.query(Checksum) \
                          .filter_by(version_id=version.id,
                                     path=relpath,
                                     sha256=sha256) \
                          .first()
        if checksum:
            break # ASSUMPTION: if *a* checksum of this package has already
                  # been added to the db in the past, then *all* of them have,
                  # as additions are part of the same transaction
        checksum = Checksum(version, relpath, sha256)
        session.add(checksum)

def debsources_main(debsources):
    debsources['subscribe']('add-package', add_package, title='checksums')
    # note: nothing to do in rm-package to counter the addition, as all
    # checksums will be removed by ON DELETE CASCADE
