# Copyright (C) 2013-2014  Stefano Zacchiroli <zack@upsilon.cc>
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
from sqlalchemy import sql, not_

import charts
import consts
import dbutils
import fs_storage
import statistics

from debmirror import SourceMirror, SourcePackage
from models import SuitesMapping, Version, HistorySize, HistorySlocCount
from subprocess_workaround import subprocess_setup

KNOWN_EVENTS = [ 'add-package', 'rm-package' ]
NO_OBSERVERS = dict( [ (e, []) for e in KNOWN_EVENTS ] )

# maximum number of pending rows before performing a (bulk) insert
BULK_FLUSH_THRESHOLD = 50000


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

def notify(observers, conf, event, session, pkg, pkgdir, file_table=None):
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

    * file_table: a dictionary mapping file names to DB file identifiers
      (unique integers). If != None, the hook can rely on the file_table keys
      to avoid re-scanning the file-system and use the corresponding file IDs.
      If None, the hook will have to redo the scanning work.

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
        subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                preexec_fn=subprocess_setup)
    except subprocess.CalledProcessError, e:
        logging.error('shell hooks for %s on %s returned exit code %d. Output: %s'
                      % (event, pkg, e.returncode, e.output))
        raise e

    notify_plugins(observers, event, session, pkg, pkgdir,
                   file_table=file_table)


def notify_plugins(observers, event, session, pkg, pkgdir,
                   triggers=None, dry=False, file_table=None):
    """notify Python hooks of occurred events

    If triggers is not None, only Python hooks whose names are listed in them
    will be triggered. Note: shell hooks will not be triggered in that case.
    """
    for (title, action) in observers[event]:
        try:
            if triggers is None:
                action(session, pkg, pkgdir, file_table)
            elif (event, title) in triggers:
                logging.info('notify (forced) %s/%s for %s' % (event, title, pkg))
                if not dry:
                    action(session, pkg, pkgdir, file_table)
        except:
            logging.error('plugin hooks for %s on %s failed' % (event, pkg))
            raise


def ensure_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def ensure_cache_dir(conf):
    ensure_dir(conf['cache_dir'])

def ensure_stats_dir(conf):
    ensure_dir(os.path.join(conf['cache_dir'], 'stats'))


def extract_new(status, conf, session, mirror, observers=NO_OBSERVERS):
    """update stage: list mirror and extract new packages

    """
    ensure_cache_dir(conf)

    def extract_package(pkg):
        pkgdir = pkg.extraction_dir(conf['sources_dir'])
        if not dbutils.lookup_version(session, pkg['package'], pkg['version']):
            try:
                logging.info('add %s...' % pkg)
                if not conf['dry_run'] and 'fs' in conf['backends']:
                    fs_storage.extract_package(pkg, pkgdir)
                with session.begin_nested():
                    # single db session for package addition and hook
                    # execution: if the hooks fail, the package won't be
                    # added to the db (it will be tried again at next run)
                    file_table = None
                    if not conf['dry_run'] and 'db' in conf['backends']:
                        file_table = dbutils.add_package(session, pkg, pkgdir)
                    if not conf['dry_run'] and 'hooks' in conf['backends']:
                        notify(observers, conf,
                               'add-package', session, pkg, pkgdir, file_table)
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

    logging.info('add new packages...')
    for pkg in mirror.ls():
        if not conf['single_transaction']:
            with session.begin():
                extract_package(pkg)
        else:
            extract_package(pkg)


def garbage_collect(status, conf, session, mirror, observers=NO_OBSERVERS):
    """update stage: list db and remove disappeared and expired packages

    """
    logging.info('garbage collection...')
    for version in session.query(Version).filter(not_(Version.sticky)):
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
                    if not conf['dry_run'] and 'hooks' in conf['backends']:
                        notify(observers, conf,
                               'rm-package', session, pkg, pkgdir)
                    if not conf['dry_run'] and 'fs' in conf['backends']:
                        fs_storage.remove_package(pkg, pkgdir)
                    if not conf['dry_run'] and 'db' in conf['backends']:
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
    """update stage: sweep and recreate suite mappings

    """
    logging.info('update suites mappings...')

    if not conf['dry_run'] and 'db' in conf['backends']:
        session.query(SuitesMapping).delete()

    insert_q = sql.insert(SuitesMapping.__table__)
    insert_params = []
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
                params = { 'sourceversion_id': version.id,
                           'suite': suite }
                insert_params.append(params)
                if status.sources.has_key(pkg_id):
                    # fill-in incomplete suite information in status
                    status.sources[pkg_id][-1].append(suite)
                else:
                    # defensive measure to make update_suites() more reusable
                    logging.warn('cannot find package %s/%s in status during suite update'
                                 % (pkg, version))
        if not conf['dry_run'] and 'db' in conf['backends'] \
           and len(insert_params) >= BULK_FLUSH_THRESHOLD:
            session.execute(insert_q, insert_params)
            session.flush()
            insert_params = []
    if not conf['dry_run'] and 'db' in conf['backends'] \
       and insert_params:
        session.execute(insert_q, insert_params)
        session.flush()

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
    """update stage: update statistics

    """
    # TODO conf['dry_run'] unused in this function, should be used

    logging.info('update statistics...')
    ensure_cache_dir(conf)

    def store_sloccount_stats(summary, d, prefix, db_obj):
        """Update stats dictionary `d`, and DB object `db_obj`, with per-language
        sloccount statistics available in `summary`, generating dictionary keys
        that start with `prefix`. Missing languages in summary will be stored
        as 0-value entries.

        """
        total_slocs = 0
        for lang in consts.SLOCCOUNT_LANGUAGES:
            k = prefix + '.' +  lang
            v = 0
            if summary.has_key(lang):
                v = summary[lang]
            d[k] = v
            setattr(db_obj, 'lang_' + lang, v)
            total_slocs += v
        d[prefix] = total_slocs

    now = datetime.utcnow()

    # compute overall stats
    suite = 'ALL'
    siz = HistorySize(suite, timestamp=now)
    loc = HistorySlocCount(suite, timestamp=now)
    stats = {}
    for stat in ['disk_usage', 'source_packages', 'source_files', 'ctags']:
        v = getattr(statistics, stat)(session)
        stats['total.' + stat] = v
        setattr(siz, stat, v)
    store_sloccount_stats(statistics.sloccount_summary(session),
                          stats, 'total.sloccount', loc)
    session.add(siz)
    session.add(loc)

    # compute per-suite stats
    for suite in statistics.suites(session):
        siz = HistorySize(suite, timestamp=now)
        loc = HistorySlocCount(suite, timestamp=now)

        suite_key = 'debian_' + suite + '.'
        for stat in ['disk_usage', 'source_packages', 'source_files', 'ctags']:
            v = getattr(statistics, stat)(session, suite)
            stats[suite_key + stat] = v
            setattr(siz, stat, v)
        store_sloccount_stats(statistics.sloccount_summary(session, suite),
                              stats, suite_key + 'sloccount', loc)
        session.add(siz)
        session.add(loc)

    session.flush()

    # cache computed stats to on-disk stats file
    stats_file = os.path.join(conf['cache_dir'], 'stats.data')
    with open(stats_file, 'w') as out:
        for k, v in sorted(stats.iteritems()):
            out.write('%s\t%d\n' % (k, v))


def update_metadata(status, conf, session):
    """update stage: update metadata

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


def update_charts(status, conf, session):
    """update stage: rebuild charts"""

    logging.info('update charts...')
    ensure_stats_dir(conf)

    CHARTS = [	# <period, granularity> paris
        ('1 month', 'hourly'),
        ('1 year', 'daily'),
        ('5 years', 'weekly'),
        ('20 years', 'monthly'),
    ]

    # size charts, various metrics
    for metric in ['source_packages', 'disk_usage', 'source_files', 'ctags']:
        for (period, granularity) in CHARTS:
            for suite in statistics.suites(session) + ['ALL']:
                series = getattr(statistics, 'history_size_' + granularity) \
                         (session, metric, interval=period, suite=suite)
                chart_file = os.path.join(conf['cache_dir'], 'stats', \
                        '%s-%s-%s.png' % \
                            (suite, metric, period.replace(' ', '-')))
                if not conf['dry_run']:
                    charts.size_plot(series, chart_file)

    # sloccount: historical histograms
    for (period, granularity) in CHARTS:
        for suite in statistics.suites(session) + ['ALL']:
            # historical histogram
            mseries = getattr(statistics, 'history_sloc_' + granularity) \
                      (session, interval=period, suite=suite)
            chart_file = os.path.join(conf['cache_dir'], 'stats', \
                    '%s-sloc-%s.png' % (suite, period.replace(' ', '-')))
            if not conf['dry_run']:
                charts.sloc_plot(mseries, chart_file)

    # sloccount: current pie charts
    for suite in statistics.suites(session) + ['ALL']:
        sloc_suite = suite
        if sloc_suite == 'ALL':
            sloc_suite = None
        slocs = statistics.sloccount_summary(session, suite=sloc_suite)
        chart_file = os.path.join(conf['cache_dir'], 'stats', \
                                  '%s-sloc_pie-current.png' % suite)
        charts.sloc_pie(slocs, chart_file)


(STAGE_EXTRACT,
 STAGE_SUITES,
 STAGE_GC,
 STAGE_STATS,
 STAGE_CACHE,
 STAGE_CHARTS,) = range(1, 7)
UPDATE_STAGES = set(range(1, 7))

def update(conf, session, observers=NO_OBSERVERS, stages=UPDATE_STAGES):
    """do a full update run
    """
    logging.info('start')
    logging.info('list mirror packages...')
    mirror = SourceMirror(conf['mirror_dir'])
    status = UpdateStatus()

    if STAGE_EXTRACT in stages:
        extract_new(status, conf, session, mirror, observers)	# stage 1
    if STAGE_SUITES in stages:
        update_suites(status, conf, session, mirror)		# stage 2
    if STAGE_GC in stages:
        garbage_collect(status, conf, session, mirror, observers)# stage 3
    if STAGE_STATS in stages:
        update_statistics(status, conf, session)		# stage 4
    if STAGE_CACHE in stages:
        update_metadata(status, conf, session)			# stage 5
    if STAGE_CHARTS in stages:
        update_charts(status, conf, session)			# stage 6

    logging.info('finish')
