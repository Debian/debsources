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
import string
import subprocess

from datetime import datetime
from email.utils import formatdate
from sqlalchemy import distinct

import consts
import dbutils
import fs_storage
import statistics

from debmirror import SourceMirror, SourcePackage
from models import SuitesMapping, Version

KNOWN_EVENTS = [ 'add-package', 'rm-package' ]
NO_OBSERVERS = dict( [ (e, []) for e in KNOWN_EVENTS ] )


class UpdateStatus(object):
    """store update status during update runs"""

    def __init__(self):
        self._sources = {}

    @property
    def sources(self):
        """entries for the on-disk cache of source packages (AKA sources.txt)

        sources is a dictionary from pairs <SRC_NAME, SRC_VERSION> to tuples
        <AREA, DSC, UNPACK_DIR, SUITES>, where SUITES is a list of SUITE_NAMEs

        """
        return self._sources

    @sources.setter
    def sources(self, new_sources):
        self._sources = new_sources


# TODO fill tables: BinaryPackage, BinaryVersion
# TODO get rid of shell hooks; they shall die a horrible death

def notify(observers, conf, event, session, pkg, pkgdir):
    """notify (Python and shell) hooks of occurred events

    Currently supported events:

    * add-package: a package is being added to Debsources; its source files
      have already been unpacked to the file storage and its metadata have
      already been added to the database

    * rm-package: a package is being removed from Debsources; its source files
      are still part of the file storage and its metadata are still part of the
      database

    Python hooks are passed the following arguments, in this order:

    * session: ongoing database session; failures in hook execution will cause
      the session to be rolled back, udoing pending database modifications
      (e.g. the addition/removal of package metadata)

    * pkg: a debmirror.SourcePackage representation of the package being acted
      upon

    * pkgdir: path pointing to the package location in the file storage

    Shell hoks re invoked with the following arguments: pkgdir, package name,
    package version

    """
    logging.debug('notify %s for %s' % (event, pkg))
    package, version = pkg['package'], pkg['version']
    cmd = ['run-parts', '--exit-on-error',
           '--arg', pkgdir,
           '--arg', package,
           '--arg', version,
           os.path.join(conf['bin_dir'], event + '.d')
       ]

    # fire shell hooks
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, e:
        logging.error('shell hooks for %s on %s returned exit code %d. Output: %s'
                      % (event, pkg, e.returncode, e.output))
        raise e

    notify_plugins(observers, event, session, pkg, pkgdir)


def notify_plugins(observers, event, session, pkg, pkgdir,
                   triggers=None, dry=False):
    """notify Python hooks of occurred events

    If triggers is not None, only Python hooks whose names are listed in them
    will be triggered. Note: shell hooks will not be triggered in that case.
    """
    for (title, action) in observers[event]:
        try:
            if triggers is None:
                action(session, pkg, pkgdir)
            elif (event, title) in triggers:
                logging.info('notify (forced) %s/%s for %s' % (event, title, pkg))
                if not dry:
                    action(session, pkg, pkgdir)
        except:
            logging.error('plugin hooks for %s on %s failed' % (event, pkg))
            raise


def ensure_cache_dir(conf):
    if not os.path.exists(conf['cache_dir']):
        os.makedirs(conf['cache_dir'])


def extract_new(status, conf, session, mirror, observers=NO_OBSERVERS):
    """update phase: list mirror and extract new packages

    """
    ensure_cache_dir(conf)

    logging.info('add new packages...')
    for pkg in mirror.ls():
        pkgdir = pkg.extraction_dir(conf['sources_dir'])
        if not dbutils.lookup_version(session, pkg['package'], pkg['version']):
            try:
                logging.info('add %s...' % pkg)
                if not conf['dry_run'] and 'fs' in conf['passes']:
                    fs_storage.extract_package(pkg, pkgdir)
                with session.begin_nested():
                    # single db session for package addition and hook
                    # execution: if the hooks fail, the package won't be
                    # added to the db (it will be tried again at next run)
                    if not conf['dry_run'] and 'db' in conf['passes']:
                        dbutils.add_package(session, pkg)
                    if not conf['dry_run'] and 'hooks' in conf['passes']:
                        notify(observers, conf,
                               'add-package', session, pkg, pkgdir)
            except:
                logging.exception('failed to extract %s' % pkg)
        if conf['force_triggers']:
            try:
                notify_plugins(observers, 'add-package', session, pkg, pkgdir,
                               triggers=conf['force_triggers'], dry=conf['dry_run'])
            except:
                logging.exception('trigger failure on %s' % pkg)
        # add entry for sources.txt, temporarily with no suite associated
        pkg_id = (pkg['package'], pkg['version'])
        status.sources[pkg_id] = pkg.archive_area(), pkg.dsc_path(), pkgdir, []


def garbage_collect(status, conf, session, mirror, observers=NO_OBSERVERS):
    """update phase: list db and remove disappeared and expired packages

    """
    logging.info('garbage collection...')
    for version in session.query(Version).all():
        pkg = SourcePackage.from_db_model(version)
        pkg_id = (pkg['package'], pkg['version'])
        pkgdir = pkg.extraction_dir(conf['sources_dir'])
        if not pkg_id in mirror.packages:
            # package is in in Debsources db, but gone from mirror: we
            # might have to garbage collect it (depending on expiry)
            try:
                expire_days = conf['expire_days']
                age = None
                if os.path.exists(pkgdir):
                    age = datetime.now() \
                          - datetime.fromtimestamp(os.path.getmtime(pkgdir))
                if not age or age.days >= expire_days:
                    logging.info("gc %s..." % pkg)
                    if not conf['dry_run'] and 'hooks' in conf['passes']:
                        notify(conf, 'rm-package', session, pkg, pkgdir)
                    if not conf['dry_run'] and 'fs' in conf['passes']:
                        fs_storage.remove_package(pkg, pkgdir)
                    if not conf['dry_run'] and 'db' in conf['passes']:
                        with session.begin_nested():
                            dbutils.rm_package(session, pkg, version)
                else:
                    logging.debug('not removing %s as it is too young' % pkg)
            except:
                logging.exception('failed to remove %s' % pkg)
        if conf['force_triggers']:
            try:
                notify_plugins(observers, 'rm-package', session, pkg, pkgdir,
                               triggers=conf['force_triggers'], dry=conf['dry_run'])
            except:
                logging.exception('trigger failure on %s' % pkg)


def update_suites(status, conf, session, mirror):
    """update phase: sweep and recreate suite mappings

    """
    logging.info('update suites mappings...')
    if not conf['dry_run']:
        session.query(SuitesMapping).delete()
    for (suite, pkgs) in mirror.suites.iteritems():
        for pkg_id in pkgs:
            (pkg, version) = pkg_id
            version = dbutils.lookup_version(session, pkg, version)
            if not version:
                logging.warn('cannot find package %s/%s mentioned by suite %s, skipping'
                             % (pkg, version, suite))
            else:
                logging.debug('add suite mapping: %s/%s -> %s'
                              % (pkg, version, suite))
                if not conf['dry_run']:
                    suite_entry = SuitesMapping(version, suite)
                    session.add(suite_entry)
                if status.sources.has_key(pkg_id):
                    # fill-in incomplete suite information in status
                    status.sources[pkg_id][-1].append(suite)
                else:
                    # defensive measure to make update_suites() more reusable
                    logging.warn('cannot find package %s/%s in status during suite update'
                                 % (pkg, version))

    # update sources.txt, now that we know the suite mappings
    src_list_path = os.path.join(conf['cache_dir'], 'sources.txt')
    with open(src_list_path + '.new', 'w') as src_list:
        for pkg_id, src_entry in status.sources.iteritems():
            fields = list(pkg_id)
            fields.extend(src_entry[:-1])	# all except suites
            fields.append(string.join(src_entry[-1], ','))
            src_list.write(string.join(fields, '\t') + '\n')
    os.rename(src_list_path + '.new', src_list_path)


def update_statistics(status, conf, session):
    """update phase: update statistics

    """
    # TODO conf['dry_run'] unused in this function, should be used

    logging.info('update statistics...')
    ensure_cache_dir(conf)

    def store_sloccount_stats(summary, d, prefix_fmt):
        """Update stats dictionary d with per-language sloccount statistics available
        in summary, using prefix_fmt as the format string to create dictionary
        keys. %s in the format string will be replaced by the language name.
        Missing languages in summary will be stored as 0-value entries.

        """
        for lang in consts.SLOCCOUNT_LANGUAGES:
            k = prefix_fmt % lang
            v = 0
            if summary.has_key(lang):
                v = summary[lang]
            d[k] = v

    # compute stats
    stats = {}
    stats['size'] = statistics.size(session)
    store_sloccount_stats(statistics.sloccount_summary(session),
                          stats, 'sloccount.%s')
    for suite in session.query(distinct(SuitesMapping.suite)).all():
        suite = suite[0]	# SQL projection of the only field
        stats['size.debian_' + suite] = statistics.size(session, suite)
        slocs = statistics.sloccount_summary(session, suite)
        store_sloccount_stats(slocs, stats, 'sloccount.%s.debian_' + suite)
        slocs_suite = reduce(lambda locs,acc: locs+acc, slocs.itervalues())
        stats['sloccount.debian_' + suite] = slocs_suite

    # cache computed stats to on-disk stats file
    stats_file = os.path.join(conf['cache_dir'], 'stats.data')
    with open(stats_file, 'w') as out:
        for k, v in sorted(stats.iteritems()):
            out.write('%s\t%d\n' % (k, v))


def update_metadata(status, conf, session):
    """update phase: update metadata

    """
    # TODO conf['dry_run'] unused in this function, should be used

    logging.info('update metadata...')
    ensure_cache_dir(conf)

    # update package prefixes list
    with open(os.path.join(conf['cache_dir'], 'pkg-prefixes'), 'w') as out:
        for prefix in SourceMirror(conf['mirror_dir']).pkg_prefixes():
            out.write('%s\n' % prefix)

    # update timestamp
    timestamp_file = os.path.join(conf['cache_dir'], 'last-update')
    with open(timestamp_file, 'w') as out:
        out.write('%s\n' % formatdate())


def update(conf, session, observers=NO_OBSERVERS):
    """do a full update run
    """
    logging.info('start')
    logging.info('list mirror packages...')
    mirror = SourceMirror(conf['mirror_dir'])
    status = UpdateStatus()

    extract_new(status, conf, session, mirror, observers)	# phase 1
    update_suites(status, conf, session, mirror)		# phase 2
    garbage_collect(status, conf, session, mirror, observers)	# phase 3
    update_statistics(status, conf, session)			# phase 4
    update_metadata(status, conf, session)			# phase 5

    logging.info('finish')
