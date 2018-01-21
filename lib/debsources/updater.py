# Copyright (C) 2013-2014  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING

from __future__ import absolute_import
from __future__ import division

import glob
import logging
import os
import string
import subprocess

import six
from six.moves import map
from six.moves import range

from datetime import datetime
from email.utils import formatdate
from sqlalchemy import sql, not_

from debsources import db_storage
from debsources import fs_storage
from debsources import statistics
from . import query as qry

from debsources.consts import DEBIAN_RELEASES, SLOCCOUNT_LANGUAGES
from debsources.debmirror import SourceMirror, SourcePackage
from debsources.models import SuiteInfo, Suite, SuiteAlias, Package, \
    HistorySize, HistorySlocCount, HistoryCopyright
from debsources.subprocess_workaround import subprocess_setup

KNOWN_EVENTS = ['add-package', 'rm-package']
NO_OBSERVERS = dict([(e, []) for e in KNOWN_EVENTS])

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

def notify(conf, event, session, pkg, pkgdir, file_table=None):
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
           os.path.join(conf['bin_dir'], event + '.d')]

    # fire shell hooks
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                preexec_fn=subprocess_setup)
    except subprocess.CalledProcessError as e:
        logging.error('shell hooks for %s on %s returned exit code %d.'
                      ' Output: %s'
                      % (event, pkg, e.returncode, e.output))
        raise e

    notify_plugins(conf['observers'], event, session, pkg, pkgdir,
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
                logging.info('notify (forced) %s/%s for %s'
                             % (event, title, pkg))
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


def exclude_files(session, pkg, pkgdir, file_table, exclude_specs):
    """remove files matching `exclude_specs` from storage and exclude them from
    further processing

    Side effect: excluded files will be removed from `file_table`

    """
    # enforce spec's Package field
    specs = [spec for spec in exclude_specs
             # ignore non file-based exclusion stanzas
             if 'files' in spec and
             spec['package'] == pkg['package']]
    candidates = []  # files eligible for exclusion
    for spec in specs:
        # enforce spec's Files field
        for pat in spec['files'].split():
            # ASSUMPTION: `pkgdir` is the CWD; enforced by _add_package
            for relpath in glob.iglob(pat):
                candidates.append(relpath)

    # remove exclusion candidates from FS and DB storage
    if candidates:
        logging.info('excluding some files from %s' % pkg)
        for relpath in candidates:
            logging.debug('excluding file %s' % relpath)
            fs_storage.rm_file(pkgdir, relpath)
            db_storage.rm_file(session, pkg['package'], relpath, file_table)
            del(file_table[relpath])


def is_excluded_package(pkg, exclude_specs):
    """check whether a given package match 1+ package exclusion stanzas

    """
    # compute list of *matching* package exclusion stanzas
    specs = [spec for spec in exclude_specs
             # ignore non package exclusion stanzas
             if 'files' not in spec and
             spec['package'] == pkg['package'] and
             ('version' not in spec or
              spec['version'] == pkg['version'])]
    return bool(specs)


def _add_package(pkg, conf, session, sticky=False):
    """add package `pkg` to both FS and DB storage, and notify plugins

    handles and logs exceptions
    """
    logging.info('add %s...' % pkg)
    workdir = os.getcwd()
    try:
        pkgdir = pkg.extraction_dir(conf['sources_dir'])
        if pkgdir is None:
            logging.warning('package %s has no extracion dir, skipping' % pkg)
            return
        if not conf['dry_run'] and 'fs' in conf['backends']:
            fs_storage.extract_package(pkg, pkgdir)
            os.chdir(pkgdir)
        with session.begin_nested():
            # single db session for package addition and hook execution: if the
            # hooks fail, the package won't be added to the db (it will be
            # tried again at next run)
            file_table = None
            if not conf['dry_run'] and 'db' in conf['backends']:
                file_table = db_storage.add_package(session, pkg, pkgdir,
                                                    sticky)
            exclude_files(session, pkg, pkgdir, file_table, conf['exclude'])
            if not conf['dry_run'] and 'hooks' in conf['backends']:
                notify(conf, 'add-package', session, pkg, pkgdir, file_table)
    except:
        logging.exception('failed to add %s' % pkg)
    finally:
        os.chdir(workdir)


def _rm_package(pkg, conf, session, db_package=None):
    """remove package `pkg` from both FS and DB storage, and notify plugins

    handles and logs exceptions
    """
    logging.info("remove %s..." % pkg)
    pkgdir = pkg.extraction_dir(conf['sources_dir'])
    if not db_package:
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        if not db_package:
            logging.warn('cannot find package %s, not removing' % pkg)
            return
    try:
        if not conf['dry_run'] and 'hooks' in conf['backends']:
            notify(conf, 'rm-package', session, pkg, pkgdir)
        if not conf['dry_run'] and 'fs' in conf['backends']:
            fs_storage.remove_package(pkg, pkgdir)
        if not conf['dry_run'] and 'db' in conf['backends']:
            if not conf['single_transaction']:
                with session.begin():
                    db_storage.rm_package(session, pkg, db_package)
            else:
                with session.begin_nested():
                    db_storage.rm_package(session, pkg, db_package)
    except:
        logging.exception('failed to remove %s' % pkg)


def _add_suite(conf, session, suite, sticky=False, aliases=[]):
    """add suite to the table of static suite info

    """
    suite_version = None
    suite_reldate = None
    if suite in DEBIAN_RELEASES:
        suite_info = DEBIAN_RELEASES[suite]
        suite_version = suite_info['version']
        suite_reldate = suite_info['date']
        if sticky:
            assert suite_info['archived']
    db_aliases = [SuiteAlias(alias=alias, suite=suite) for alias in aliases]
    db_suite = SuiteInfo(suite, sticky=sticky,
                         version=suite_version,
                         release_date=suite_reldate,
                         aliases=db_aliases)
    if not conf['dry_run'] and 'db' in conf['backends']:
        session.add(db_suite)


def extract_new(status, conf, session, mirror):
    """update stage: list mirror and extract new packages

    """
    ensure_cache_dir(conf)

    def add_package(pkg):
        if is_excluded_package(pkg, conf['exclude']):
            logging.info('skipping excluded package %s' % pkg)
            return
        if not db_storage.lookup_package(session, pkg['package'],
                                         pkg['version']):
            # use DB as completion marker: if the package has been inserted, it
            # means everything went fine last time we tried. If not, we redo
            # everything, just to be safe
            _add_package(pkg, conf, session)
        pkgdir = pkg.extraction_dir(conf['sources_dir'])
        if conf['force_triggers']:
            try:
                notify_plugins(conf['observers'], 'add-package',
                               session, pkg, pkgdir,
                               triggers=conf['force_triggers'],
                               dry=conf['dry_run'])
            except:
                logging.exception('trigger failure on %s' % pkg)
        # add entry for sources.txt, temporarily with no suite associated
        pkg_id = (pkg['package'], pkg['version'])
        dsc_rel = os.path.relpath(pkg.dsc_path(), conf['mirror_dir'])
        pkgdir_rel = os.path.relpath(pkg.extraction_dir(conf['sources_dir']),
                                     conf['sources_dir'])
        status.sources[pkg_id] = pkg.archive_area(), dsc_rel, pkgdir_rel, []

    logging.info('add new packages...')
    for pkg in mirror.ls():
        if not conf['single_transaction']:
            with session.begin():
                add_package(pkg)
        else:
            add_package(pkg)


def garbage_collect(status, conf, session, mirror):
    """update stage: list db and remove disappeared and expired packages

    """
    logging.info('garbage collection...')
    for version in session.query(Package).filter(not_(Package.sticky)):
        pkg = SourcePackage.from_db_model(version)
        pkg_id = (pkg['package'], pkg['version'])
        pkgdir = pkg.extraction_dir(conf['sources_dir'])
        if pkg_id not in mirror.packages:
            # package is in in Debsources db, but gone from mirror: we
            # might have to garbage collect it (depending on expiry)
            expire_days = conf['expire_days']
            age = None
            if os.path.exists(pkgdir):
                age = datetime.now() - \
                    datetime.fromtimestamp(os.path.getmtime(pkgdir))
            if not age or age.days >= expire_days:
                _rm_package(pkg, conf, session, db_package=version)
            else:
                logging.debug('not removing %s as it is too young' % pkg)

        if conf['force_triggers']:
            try:
                notify_plugins(conf['observers'], 'rm-package',
                               session, pkg, pkgdir,
                               triggers=conf['force_triggers'],
                               dry=conf['dry_run'])
            except:
                logging.exception('trigger failure on %s' % pkg)


def update_suites(status, conf, session, mirror):
    """update stage: sweep and recreate suite mappings

    """
    logging.info('update suites mappings...')

    insert_q = sql.insert(Suite.__table__)
    insert_params = []

    # load suites aliases
    suites_aliases = mirror.ls_suites_with_aliases()
    if not conf['dry_run'] and 'db' in conf['backends']:
        session.query(SuiteAlias).delete()

    for (suite, pkgs) in six.iteritems(mirror.suites):
        if not conf['dry_run'] and 'db' in conf['backends']:
            session.query(Suite).filter_by(suite=suite).delete()
        for pkg_id in pkgs:
            (pkg, version) = pkg_id
            db_package = db_storage.lookup_package(session, pkg, version)
            if not db_package:
                logging.warn('package %s/%s not found in suite %s, skipping'
                             % (pkg, version, suite))
            else:
                logging.debug('add suite mapping: %s/%s -> %s'
                              % (pkg, version, suite))
                params = {'package_id': db_package.id,
                          'suite': suite}
                insert_params.append(params)
                if pkg_id in status.sources:
                    # fill-in incomplete suite information in status
                    status.sources[pkg_id][-1].append(suite)
                else:
                    # defensive measure to make update_suites() more reusable
                    logging.warn('cannot find %s/%s during suite update'
                                 % (pkg, version))
        if not conf['dry_run'] and 'db' in conf['backends'] \
           and len(insert_params) >= BULK_FLUSH_THRESHOLD:
            session.execute(insert_q, insert_params)
            session.flush()
            insert_params = []

        if not conf['dry_run'] and 'db' in conf['backends']:
            session.query(SuiteInfo).filter_by(name=suite).delete()
            _add_suite(conf, session, suite, aliases=suites_aliases[suite])

    if not conf['dry_run'] and 'db' in conf['backends'] \
       and insert_params:
        session.execute(insert_q, insert_params)
        session.flush()

    # update sources.txt, now that we know the suite mappings
    src_list_path = os.path.join(conf['cache_dir'], 'sources.txt')
    with open(src_list_path + '.new', 'w') as src_list:
        for pkg_id, src_entry in six.iteritems(status.sources):
            fields = list(pkg_id)
            fields.extend(src_entry[:-1])  # all except suites
            fields.append(string.join(src_entry[-1], ','))
            src_list.write(string.join(fields, '\t') + '\n')
    os.rename(src_list_path + '.new', src_list_path)


def __target_suites(session, suites=None):
    if not suites:
        sticky_suites = statistics.sticky_suites(session)
        suites = [suite
                  for suite in statistics.suites(session, suites='all')
                  if suite not in sticky_suites]
    return suites


def update_statistics(status, conf, session, suites=None):
    """update stage: update statistics

    by default act on all non-sticky, major suites present in the DB. Pass
    `suites` to override

    """
    logging.info('update statistics...')
    ensure_cache_dir(conf)
    suites = __target_suites(session, suites)

    now = datetime.utcnow()
    stats_file = os.path.join(conf['cache_dir'], 'stats.data')
    if os.path.exists(stats_file):
        # If stats.data exists, load and update it, otherwise start from
        # scratch. Note: this means that we need to be careful about changing
        # stats keys, to avoid orphans.
        # TODO: add check about orphan stats.data entries to debsources-fsck
        stats = statistics.load_metadata_cache(stats_file)
    else:
        stats = {}

    def store_sloccount_stats(summary, d, prefix, db_obj):
        """Update stats dictionary `d`, and DB object `db_obj`, with per
        language sloccount statistics available in `summary`, generating
        dictionary keys that start with `prefix`. Missing languages in summary
        will be stored as 0-value entries.

        """
        total_slocs = 0
        for lang in SLOCCOUNT_LANGUAGES:
            k = prefix + '.' + lang
            v = 0
            if lang in summary:
                v = summary[lang]
            d[k] = v
            setattr(db_obj, 'lang_' + lang, v)
            total_slocs += v
        d[prefix] = total_slocs

    # compute overall stats
    suite = 'ALL'
    siz = HistorySize(suite, timestamp=now)
    loc = HistorySlocCount(suite, timestamp=now)
    for stat in ['disk_usage', 'source_packages', 'source_files', 'ctags']:
        v = getattr(statistics, stat)(session)
        stats['total.' + stat] = v
        setattr(siz, stat, v)
    store_sloccount_stats(statistics.sloccount_summary(session),
                          stats, 'total.sloccount', loc)
    if not conf['dry_run'] and 'db' in conf['backends']:
        session.add(siz)
        session.add(loc)

    # Update HistorySize
    suite_key = 'debian_'
    hist_siz = dict((suite, HistorySize(suite, timestamp=now))
                    for suite in suites)
    for stat in ['disk_usage', 'source_packages', 'source_files', 'ctags']:
        stats_result = statistics.stats_grouped_by(session, stat)
        for res in stats_result:
            if res[0] in suites:
                stats[suite_key + res[0] + '.' + stat] = res[1]
                setattr(hist_siz[res[0]], stat, res[1])

    if not conf['dry_run'] and 'db' in conf['backends']:
        for siz in hist_siz.values():
            session.add(siz)

    # update historySlocCount
    sloccount_res = statistics.stats_grouped_by(session, 'sloccount')
    hist_loc = dict((suite, HistorySlocCount(suite, timestamp=now))
                    for suite in suites)
    for suite in suites:
        temp = dict((item[1], item[2]) for item in sloccount_res
                    if item[0] == suite)
        store_sloccount_stats(dict(temp), stats,
                              suite_key + suite + ".sloccount",
                              hist_loc[suite])

    if not conf['dry_run'] and 'db' in conf['backends']:
        for loc in hist_loc.values():
            session.add(loc)

    session.flush()

    # cache computed stats to on-disk stats file
    if not conf['dry_run'] and 'fs' in conf['backends']:
        statistics.save_metadata_cache(stats, stats_file)

    def update_license_statistics(suites):
        # compute License stats
        license_stats_file = os.path.join(conf['cache_dir'],
                                          'license_stats.data')
        dual_license_file = os.path.join(conf['cache_dir'],
                                         'dual_license.data')
        license_stats = dict()
        license_d_stats = dict()

        hist_lic = dict((suite, HistoryCopyright(suite, timestamp=now))
                        for suite in suites)
        results = statistics.get_licenses(session)
        for suite in suites:
            temp = dict((item[0], item[2]) for item in results
                        if item[1] == suite)
            summary = statistics.licenses_summary(temp)
            for res in summary:
                license_stats[suite + "." + res.rstrip()] = summary[res]
                setattr(hist_lic[suite], 'license', res.replace('_', ' '))
                setattr(hist_lic[suite], 'files', summary[res])
                if not conf['dry_run'] and 'db' in conf['backends']:
                        session.add(hist_lic[suite])
            # no historical here, only save to file
            dual_query = statistics.licenses_summary_w_dual(temp)
            for res in dual_query:
                license_d_stats[suite + "." + res.rstrip()] = dual_query[res]

        # overall dual licenses
        overall_d_licenses = statistics.licenses_summary_w_dual(
            statistics.get_licenses(session, 'ALL'))
        for stat in overall_d_licenses:
            license_d_stats['overall.' + stat] = overall_d_licenses[stat]

        # save dual licenses to file
        if not conf['dry_run'] and 'fs' in conf['backends']:
            statistics.save_metadata_cache(license_d_stats, dual_license_file)

        session.flush()
        overall_licenses = statistics.licenses_summary(
            statistics.get_licenses(session, 'ALL'))
        for stat in overall_licenses:
            lic = HistoryCopyright('ALL', timestamp=now)
            setattr(lic, 'license', stat.replace('_', ' '))
            setattr(lic, 'files', overall_licenses[stat])
            license_stats['overall.' + stat] = overall_licenses[stat]
            if not conf['dry_run'] and 'db' in conf['backends']:
                session.add(lic)
        session.flush()
        if not conf['dry_run'] and 'fs' in conf['backends']:
            statistics.save_metadata_cache(license_stats, license_stats_file)

    if 'copyright' in conf['hooks']:
        update_license_statistics(suites)


def update_metadata(status, conf, session):
    """update stage: update metadata

    """
    logging.info('update metadata...')
    ensure_cache_dir(conf)

    # update package prefixes list
    if not conf['dry_run'] and 'fs' in conf['backends']:
        prefix_path = os.path.join(conf['cache_dir'], 'pkg-prefixes')
        with open(prefix_path + '.new', 'w') as out:
            for prefix in db_storage.pkg_prefixes(session):
                out.write('%s\n' % prefix)
        os.rename(prefix_path + '.new', prefix_path)

    # update timestamp
    if not conf['dry_run'] and 'fs' in conf['backends']:
        timestamp_file = os.path.join(conf['cache_dir'], 'last-update')
        with open(timestamp_file + '.new', 'w') as out:
            out.write('%s\n' % formatdate())
        os.rename(timestamp_file + '.new', timestamp_file)


def update_charts(status, conf, session, suites=None):
    """update stage: rebuild charts"""

    from debsources import charts
    logging.info('update charts...')
    ensure_stats_dir(conf)
    suites = __target_suites(session, suites)

    CHARTS = [  # <period, granularity> paris
        ('1 month', 'hourly'),
        ('1 year', 'daily'),
        ('5 years', 'weekly'),
        ('20 years', 'monthly'),
    ]

    # size charts, various metrics
    for metric in ['source_packages', 'disk_usage', 'source_files', 'ctags']:
        for (period, granularity) in CHARTS:
            for suite in suites + ['ALL']:
                series = getattr(statistics, 'history_size_' + granularity)(
                    session, metric, interval=period, suite=suite)
                chart_file = os.path.join(conf['cache_dir'], 'stats',
                                          '%s-%s-%s.png' %
                                          (suite, metric,
                                           period.replace(' ', '-')))
                if not conf['dry_run']:
                    charts.size_plot(series, chart_file)

    # sloccount: historical histograms
    for (period, granularity) in CHARTS:
        for suite in suites + ['ALL']:
            # historical histogram
            mseries = getattr(statistics, 'history_sloc_' + granularity)(
                session, interval=period, suite=suite)
            chart_file = os.path.join(conf['cache_dir'], 'stats',
                                      '%s-sloc-%s.png' %
                                      (suite, period.replace(' ', '-')))
            if not conf['dry_run']:
                charts.multiseries_plot(mseries, chart_file)

    # sloccount: current pie charts
    sloc_per_suite = []
    for suite in suites + ['ALL']:
        sloc_suite = suite
        if sloc_suite == 'ALL':
            sloc_suite = None
        slocs = statistics.sloccount_summary(session, suite=sloc_suite)
        if suite not in ['ALL']:
            sloc_per_suite.append(slocs)
        chart_file = os.path.join(conf['cache_dir'], 'stats',
                                  '%s-sloc_pie-current.png' % suite)
        if not conf['dry_run']:
            charts.pie_chart(slocs, chart_file)

    # sloccount: bar chart plot
    if 'charts_top_langs' in conf.keys():
        top_langs = int(conf['charts_top_langs'])
    else:
        top_langs = 6
    chart_file = os.path.join(conf['cache_dir'], 'stats', 'sloc_bar_plot.png')
    charts.bar_chart(sloc_per_suite, suites, chart_file, top_langs, 'SLOC')

    def update_license_charts():
        # License: historical histogramms
        for (period, granularity) in CHARTS:
            for suite in suites + ['ALL']:
                mseries = getattr(statistics,
                                  'history_copyright_' + granularity)(
                    session, interval=period, suite=suite)
                chart_file = os.path.join(conf['cache_dir'], 'stats',
                                          'copyright_%s-license-%s.png' %
                                          (suite, period.replace(' ', '-')))
                if not conf['dry_run']:
                    charts.multiseries_plot(mseries, chart_file, cols=3)

        # License: overall pie chart
        overall_licenses = statistics.licenses_summary(
            statistics.get_licenses(session, 'ALL'))
        ratio = qry.get_ratio(session)
        chart_file = os.path.join(conf['cache_dir'], 'stats',
                                  'copyright_overall-license_pie.png')
        if not conf['dry_run']:
            charts.pie_chart(overall_licenses, chart_file, ratio)

        # License: bar chart and per suite pie chart.
        all_suites = statistics.sticky_suites(session) \
            + __target_suites(session, None)
        licenses_per_suite = []
        results = statistics.get_licenses(session)
        for suite in all_suites:
            temp = dict((item[0], item[2]) for item in results
                        if item[1] == suite)
            licenses = statistics.licenses_summary(temp)
            ratio = qry.get_ratio(session, suite=suite)
            # draw license pie chart
            if not conf['dry_run']:
                chart_file = os.path.join(conf['cache_dir'], 'stats',
                                          'copyright_%s'
                                          '-license_pie-current.png'
                                          % suite)
                charts.pie_chart(licenses, chart_file, ratio)

            licenses_per_suite.append(licenses)

        chart_file = os.path.join(conf['cache_dir'], 'stats',
                                  'copyright_license_bar_plot.png')
        if not conf['dry_run']:
            charts.bar_chart(licenses_per_suite, all_suites, chart_file,
                             top_langs, 'Number of files')

    # LICENSE CHARTS
    if 'copyright' in conf['hooks']:
        update_license_charts()

# update stages
(STAGE_EXTRACT,
 STAGE_SUITES,
 STAGE_GC,
 STAGE_STATS,
 STAGE_CACHE,
 STAGE_CHARTS,) = list(range(1, 7))
__STAGES = {
    'extract': STAGE_EXTRACT,
    'suites': STAGE_SUITES,
    'gc': STAGE_GC,
    'stats': STAGE_STATS,
    'cache': STAGE_CACHE,
    'charts': STAGE_CHARTS,
}
__STAGE2STR = {v: k for k, v in list(__STAGES.items())}
UPDATE_STAGES = set(__STAGES.values())


def parse_stage(s):
    try:
        return __STAGES[s]
    except KeyError:
        raise ValueError('unknown update stage %s' % s)


def parse_stages(stages):
    return set(map(parse_stage, stages.split()))


def pp_stage(stage):
    try:
        return __STAGE2STR[stage]
    except KeyError:
        raise ValueError('unknown update stage %s' % stage)


def update(conf, session, stages=UPDATE_STAGES):
    """do a full update run
    """
    logging.info('start')
    logging.info('list mirror packages...')
    mirror = SourceMirror(conf['mirror_dir'])
    status = UpdateStatus()

    if STAGE_EXTRACT in stages:
        extract_new(status, conf, session, mirror)      # stage 1
    if STAGE_SUITES in stages:
        update_suites(status, conf, session, mirror)    # stage 2
    if STAGE_GC in stages:
        garbage_collect(status, conf, session, mirror)  # stage 3
    if STAGE_STATS in stages:
        update_statistics(status, conf, session)        # stage 4
    if STAGE_CACHE in stages:
        update_metadata(status, conf, session)          # stage 5
    if STAGE_CHARTS in stages:
        update_charts(status, conf, session)            # stage 6

    logging.info('finish')
