# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#               2013  Stefano Zacchiroli <zack@upsilon.cc>
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

from sqlalchemy.sql import exists

import fs_storage

from models import Base, File, Package, Version, VCS_TYPES


def add_package(session, pkg, pkgdir, sticky=False):
    """Add `pkg` (a `debmirror.SourcePackage`) to the DB.

    If `sticky` is set, also set the corresponding bit in the versions table.

    """
    logging.debug('add to db %s...' % pkg)
    package = session.query(Package).filter_by(name=pkg['package']).first()
    if not package:
        package = Package(pkg['package'])
        session.add(package)

    version = session.query(Version) \
                     .filter_by(vnumber=pkg['version'],
                                package_id=package.id)\
                     .first()
    if not version:
        version = Version(pkg['version'], package, sticky)
        version.area = pkg.archive_area()
        if pkg.has_key('vcs-browser'):
            version.vcs_browser = pkg['vcs-browser']
        for vcs_type in VCS_TYPES:
            vcs_key = 'vcs-' + vcs_type
            if pkg.has_key(vcs_key):
                version.vcs_type = vcs_type
                version.vcs_url = pkg[vcs_key]
        package.versions.append(version)
        session.add(version)
        session.flush()	# to get a version.id, needed by File below

        # add individual source files to the File table
        file_table = {}
        for path in fs_storage.walk_pkg_files(pkgdir):
            relpath = os.path.relpath(path, pkgdir)
            file_ = File(version, relpath)
            session.add(file_)
            session.flush()
            file_table[relpath] = file_.id

        return file_table


def rm_package(session, pkg, db_version):
    """Remove a package (= debmirror.SourcePackage) from the Debsources db
    """
    logging.debug('remove from db %s...' % pkg)
    session.delete(db_version)
    if not db_version.package.versions:
        # just removed last version, get rid of package too
        session.delete(db_version.package)


def lookup_version(session, package, version):
    """Lookup a package in the Debsources db, using <package, version> as key
    """
    return session.query(Version) \
                  .join(Package) \
                  .filter(Version.vnumber==version) \
                  .filter(Package.name==package) \
                  .first()

