# Copyright (C) 2014  Stefano Zacchiroli <zack@upsilon.cc>
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

"""handle the archive of sticky suites"""

import logging
import updater

from sqlalchemy import sql

import dbutils

from debmirror import SourcePackage
from models import Suite, SuitesMapping, Version


def _list_db_suites(session):
    """list sticky suites currently present in Debsources DB

    """
    q = session.query(Suite.name).filter(Suite.sticky)
    return [ row[0] for row in q ]


def _lookup_db_suite(session, suite):
    return session.query(Suite).filter_by(name=suite, sticky=True).first()


def _lookup_suitemapping(session, db_version, suite):
    return session.query(SuitesMapping) \
                  .filter_by(sourceversion_id=db_version.id, suite=suite) \
                  .first()


def list_suites(conf, session, archive):
    """return a mapping from suite names to a dictionary `{'archive': bool, 'db':
    bool}`. The first field tells whether a suite is available via the local
    mirror archive; the second whether it is available in Debsources DB.

    """
    suites = {}	# suite name -> {'archive': bool, 'db': bool}
    def ensure_suite(suite):
        if not suites.has_key(suite):
            suites[suite] = {'archive': False, 'db': False}

    for suite in archive.ls_suites():
        ensure_suite(suite)
        suites[suite]['archive'] = True

    for suite in _list_db_suites(session):
        ensure_suite(suite)
        suites[suite]['db'] = True

    return suites


def add_suite(conf, session, suite, archive):
    logging.info('add sticky suite %s to the archive...' % suite)

    db_suite = _lookup_db_suite(session, suite)
    if not db_suite:
        db_suite = Suite(suite, sticky=True)
        session.add(db_suite)
    else:
        logging.warn('sticky suite %s already present, looking for new packages'
                     % suite)

    for pkg in archive.ls(suite):
        version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
        if version:	# avoid GC upon removal from a non-sticky suite
            if not version.sticky:
                logging.debug('setting sticky bit on %s' % pkg)
                version.sticky = True
        else:
            updater._add_package(pkg, conf, session, sticky=True)
    session.flush()	# to fill Version.id-s

    suitemap_q = sql.insert(SuitesMapping.__table__)
    suitemaps = []
    for (pkg, version) in archive.suites[suite]:
        db_version = dbutils.lookup_version(session, pkg, version)
        if not db_version:
            logging.warn('package %s/%s not found in sticky suite %s, skipping'
                         % (pkg, version, suite))
            continue
        if not _lookup_suitemapping(session, db_version, suite):
            suitemaps.append({'sourceversion_id': db_version.id,
                              'suite': suite })
    if suitemaps:
        session.execute(suitemap_q, suitemaps)


def remove_suite(conf, session, suite):
    logging.info('remove sticky suite %s from the archive...' % suite)

    db_suite = _lookup_db_suite(session, suite)
    if not db_suite:
        logging.error('sticky suite %s does not exist in DB, abort.' % suite)
        return
    sticky_suites = _list_db_suites(session)

    for version in session.query(Version) \
                          .join(SuitesMapping) \
                          .filter(SuitesMapping.suite == suite) \
                          .filter(Version.sticky):
        pkg = SourcePackage.from_db_model(version)

        other_suites = \
            session.query(SuitesMapping.suite.distinct()) \
                   .filter(SuitesMapping.sourceversion_id == version.id) \
                   .filter(SuitesMapping.suite != suite)
        other_suites = [ row[0] for row in other_suites ]
        print 'XXX other_suites', other_suites

        if not other_suites:
            updater._rm_package(pkg, conf, session, db_version=version)
        else:
            other_sticky_suites = filter(lambda s: s in sticky_suites,
                                         other_suites)
            print 'XXX other_sticky_suites', other_sticky_suites
            if not other_sticky_suites:
                # package is only listed in "live" suites, drop sticky flag
                logging.debug('clearing sticky bit on %s' % pkg)
                version.sticky = False

        suitemap = _lookup_suitemapping(session, version, suite)
        if suitemap:
            session.delete(suitemap)

    session.delete(db_suite)
