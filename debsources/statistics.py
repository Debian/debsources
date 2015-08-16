# Copyright (C) 2013-2014  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

"""Compute several statistics about Debsouces content

"""

from __future__ import absolute_import

import logging
import os

import six

from sqlalchemy import distinct
from sqlalchemy import func as sql_func

from debsources.consts import SLOCCOUNT_LANGUAGES, SUITES
from debsources.models import Checksum, Ctag, Metric, SlocCount, \
    Suite, SuiteInfo, Package, PackageName


def _count(query):
    count = query.first()[0]
    if not count:
        count = 0
    return count


def _time_series(query):
    return [(row['timestamp'], row['value']) for row in query]


def suites(session, suites='release'):
    """return a list of known suites (both sticky and live) present in the DB,
    sorted by release date

    `suites` can be used to request a subset of all known suites. "release"
    (the default) returns release names (e.g. buzz, lenny, sid), "devel"
    returns only development release name variants (e.g. *-proposed-updates,
    *-updates, *-backports, plus experimental), "all" returns the union of the
    two sets

    """
    if suites not in SUITES.keys():
        raise ValueError('unknown set of suites: %s' % suites)

    db_suites = [row[0] for row in session.query(distinct(Suite.suite))]
    db_suites = [s for s in db_suites if s in SUITES[suites]]
    by_release_date = lambda s1, s2: cmp(SUITES[suites].index(s1),
                                         SUITES[suites].index(s2))
    return sorted(db_suites, cmp=by_release_date)


def sticky_suites(session, order=None):
    """list sticky suites currently present in Debsources DB

    """
    q = session.query(SuiteInfo.name) \
               .filter(SuiteInfo.sticky == True)  # NOQA,
    # '== True' can be dropped starting with sqlalchemy >= 0.8
    if order:
        q = q.order_by("release_date")
    return [row[0] for row in q]


def disk_usage(session, suite=None, areas=None):
    """disk space used by extracted source packages

    only count disk usage relative to suite, if given

    only count disk usage relative to archive `areas`, if given

    """
    logging.debug('compute disk usage for suite %s...' % suite)
    q = session.query(sql_func.sum(Metric.value)) \
               .filter(Metric.metric == 'size')
    if suite or areas:
        q = q.join(Package)
    if suite:
        q = q.join(Suite) \
             .filter(Suite.suite == suite)
    if areas:
        q = q.filter(Package.area.in_(areas))
    return _count(q)


def source_packages(session, suite=None, areas=None):
    """(versioned) source package count

    only count packages in suite, if given

    only count packages in archive `areas`, if given

    multiple versions of the same source package count adds up to the result of
    this query. When doing per-suite queries that doesn't (shouldn't) happen,
    as each suite is (usually) guaranteed to contain at most one version of
    each packages

    """
    logging.debug('count source packages for suite %s...' % suite)
    q = session.query(sql_func.count(Package.id))
    if suite:
        q = q.join(Suite) \
            .filter(Suite.suite == suite)
    if areas:
        q = q.filter(Package.area.in_(areas))
    return _count(q)


def source_files(session, suite=None, areas=None):
    """source files count

    only count source files in suite, if given

    only count packages in archive `areas`, if given

    Return 0 if the checksum plugin is not enabled

    """
    # TODO when a separate File table will be present, this will need to be
    # adapted to use that instead of Checksum
    logging.debug('count source files for suite %s...' % suite)
    q = session.query(sql_func.count(Checksum.id))
    if suite or areas:
        q = q.join(Package)
    if suite:
        q = q.join(Suite) \
             .filter(Suite.suite == suite)
    if areas:
        q = q.filter(Package.area.in_(areas))
    return _count(q)


def sloccount_lang(session, language, suite=None, areas=None):
    """source lines of codes (SLOCs) written in a given programming language

    only count SLOCs relative to suite, if given

    only count packages in archive `areas`, if given

    """
    logging.debug('sloccount for language %s, suite %s...' % (language, suite))
    q = session.query(sql_func.sum(SlocCount.count)) \
               .filter(SlocCount.language == language)
    if suite or areas:
        q = q.join(Package)
    if suite:
        q = q.join(Suite) \
             .filter(Suite.suite == suite)
    if areas:
        q = q.filter(Package.area.in_(areas))
    return _count(q)


def sloccount_summary(session, suite=None, areas=None):
    """source lines of code (SLOCs), broken down per language

    return a language-indexed dictionary of SLOC counts

    only count LOCs relative to suite, if given

    only count packages in archive `areas`, if given

    """
    logging.debug('sloccount summary for suite %s...' % suite)
    q = session.query(SlocCount.language, sql_func.sum(SlocCount.count))
    if suite or areas:
        q = q.join(Package)
    if suite:
        q = q.join(Suite) \
             .filter(Suite.suite == suite)
    if areas:
        q = q.filter(Package.area.in_(areas))
    q = q.group_by(SlocCount.language)
    return dict(q.all())


def ctags(session, suite=None, areas=None):
    """ctags count

    only count ctags in suite, if given

    only count packages in archive `areas`, if given

    """
    logging.debug('count ctags for suite %s...' % suite)
    q = session.query(sql_func.count(Ctag.id))
    if suite or areas:
        q = q.join(Package)
    if suite:
        q = q.join(Suite) \
             .filter(Suite.suite == suite)
    if areas:
        q = q.filter(Package.area.in_(areas))
    return _count(q)


def _hist_size_sample(session, metric, interval, projection, suite=None):
    q = "\
      SELECT DISTINCT ON (%(projection)s) timestamp, %(metric)s AS VALUE \
      FROM history_size \
      WHERE timestamp >= now() - interval '%(interval)s' \
      %(filter)s \
      ORDER BY %(projection)s DESC, timestamp DESC"
    kw = {'metric': metric,
          'projection': projection,
          'interval': interval,
          'filter': ''}
    if suite:
        kw['filter'] = "AND suite = '%s'" % suite
    return _time_series(session.execute(q % kw))


def history_size_hourly(session, metric, interval, suite):
    """return recent size history of `metric`, over the past `interval`

    `interval` must be a valid Postgre time interval, see
    http://www.postgresql.org/docs/9.1/static/functions-datetime.html

    """
    logging.debug('take hourly %s sample of %s for suite %s'
                  % (metric, interval, suite))
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('hour', timestamp)",
                             suite=suite)


def history_size_daily(session, metric, interval, suite):
    """like `history_size_full`, but taking daily samples"""
    logging.debug('take daily %s sample of %s for suite %s'
                  % (metric, interval, suite))
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('day', timestamp)",
                             suite=suite)


def history_size_weekly(session, metric, interval, suite):
    """like `history_size_full`, but taking weekly samples"""
    logging.debug('take weekly %s sample of %s for suite %s'
                  % (metric, interval, suite))
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('week', timestamp)",
                             suite=suite)


def history_size_monthly(session, metric, interval, suite):
    """like `history_size_full`, but taking monthly samples"""
    logging.debug('take monthly %s sample of %s for suite %s'
                  % (metric, interval, suite))
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('month', timestamp)",
                             suite=suite)


def _hist_sloc_sample(session, interval, projection, suite=None):
    q = "\
      SELECT DISTINCT ON (%(projection)s) * \
      FROM history_sloccount \
      WHERE timestamp >= now() - interval '%(interval)s' \
      %(filter)s \
      ORDER BY %(projection)s DESC, timestamp DESC"
    kw = {'projection': projection,
          'interval': interval,
          'filter': ''}
    if suite:
        kw['filter'] = "AND suite = '%s'" % suite

    series = dict([(lang, []) for lang in SLOCCOUNT_LANGUAGES])
    samples = session.execute(q % kw)
    for row in samples:
        for lang in SLOCCOUNT_LANGUAGES:
            series[lang].append((row['timestamp'], row['lang_' + lang]))

    return series


def history_sloc_hourly(session, interval, suite):
    """return recent sloccount history, over the past `interval`. Return a
    dictionary, mapping language names (see `const.SLOCCOUNT_LANGUAGES`) to
    time series, i.e. list of pairs <timestamp, slocs>

    `interval` must be as per `history_size_full`

    """
    logging.debug('take hourly sloccount sample for suite %s' % suite)
    return _hist_sloc_sample(session, interval,
                             projection="date_trunc('hour', timestamp)",
                             suite=suite)


def history_sloc_daily(session, interval, suite):
    """like `history_sloc_full`, but taking daily samples"""
    logging.debug('take daily sloccount sample for suite %s' % suite)
    return _hist_sloc_sample(session, interval,
                             projection="date_trunc('day', timestamp)",
                             suite=suite)


def history_sloc_weekly(session, interval, suite):
    """like `history_sloc_full`, but taking weekly samples"""
    logging.debug('take weekly sloccount sample for suite %s' % suite)
    return _hist_sloc_sample(session, interval,
                             projection="date_trunc('week', timestamp)",
                             suite=suite)


def history_sloc_monthly(session, interval, suite):
    """like `history_sloc_full`, but taking monthly samples"""
    logging.debug('take monthly sloccount sample for suite %s' % suite)
    return _hist_sloc_sample(session, interval,
                             projection="date_trunc('month', timestamp)",
                             suite=suite)


def sloc_per_package(session, suite=None, areas=None):
    """return the size (in SLOC) of each package in `suite`, if given, or of
    all known packages

    only consider packages in archive `areas`, if given

    data are returned as a list of sqlalchemy keyed tuples (package) `name,
    version, sloc`

    data are returned sorted, from the largest package to the smallest

    """
    q = session.query(PackageName.name, Package.version,
                      sql_func.sum(SlocCount.count).label('sloc'))
    if suite:
        q = q.select_from(Suite)
    q = q.filter(SlocCount.package_id == Package.id) \
         .filter(Package.name_id == PackageName.id)
    if suite:
        q = q.filter(Suite.package_id == Package.id) \
             .filter(Suite.suite == suite)
    if areas:
        q = q.filter(Package.area.in_(areas))
    q = q.group_by(PackageName.name, Package.version) \
         .order_by('sloc desc, name, version')
    return q.all()


def load_metadata_cache(fname):
    """load a `stats.data` file and return its content as an integer-valued
    dictionary

    """
    stats = {}
    with open(fname) as f:
        for line in f:
            k, v = line.split(None, 1)
            stats[k] = int(v)
    return stats


def save_metadata_cache(stats, fname):
    """save a `stats.data` file, atomically, reading values from an
    integer-valued dictionary

    """
    with open(fname + '.new', 'w') as out:
        for k, v in sorted(six.iteritems(stats)):
            out.write('%s\t%d\n' % (k, v))
    os.rename(fname + '.new', fname)
