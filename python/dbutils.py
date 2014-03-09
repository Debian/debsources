# Copyright (C) 2013       Matthieu Caneill <matthieu.caneill@gmail.com>
#               2013-2014  Stefano Zacchiroli <zack@upsilon.cc>
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

from models import Base, File, Package, SuiteInfo, SuitesMapping, Version
from models import VCS_TYPES


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
                     .filter_by(version=pkg['version'],
                                name_id=package.id)\
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
        for (relpath, _abspath) in fs_storage.walk_pkg_files(pkgdir):
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
                  .filter(Version.version==version) \
                  .filter(Package.name==package) \
                  .first()


def lookup_db_suite(session, suite, sticky=False):
    return session.query(SuiteInfo) \
                  .filter_by(name=suite, sticky=sticky) \
                  .first()


def lookup_suitemapping(session, db_version, suite):
    return session.query(SuitesMapping) \
                  .filter_by(version_id=db_version.id, suite=suite) \
                  .first()



def pkg_prefixes(session):
    """extract Debian package prefixes from DB via `session`

    package prefixes are either the first 4 letters of the name (for packages
    starting with "lib") or the first letter

    """
    q = """SELECT DISTINCT(substring(name from 1 for 1)) FROM PACKAGES \
           UNION \
           SELECT DISTINCT(substring(name from 1 for 4)) FROM PACKAGES
           WHERE substring(name from 1 for 3) = 'lib'"""
    return sorted([ row[0] for row in session.execute(q) ])
