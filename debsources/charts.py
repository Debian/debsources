# Copyright (C) 2014  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

from __future__ import absolute_import

import logging
import operator

import matplotlib
import six
from six.moves import range

from itertools import cycle

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # NOQA
import matplotlib.cm as cm       # NOQA
import numpy as np               # NOQA


def _split_series(series):
    """split a time `series` (list of <x,y> points) into two lists --- one of x
    and the other of y --- excluding y which are None

    """
    xs, ys = [], []

    for x, y in series:
        if y is not None:
            xs.append(x)
            ys.append(y)

    return (xs, ys)


def size_plot(series, fname):
    """plot a single size metric from a time `series` and save it to file
    `fname`

    """
    logging.debug('generate size plot to %s...' % fname)
    ts, values = _split_series(series)

    plt.figure()
    plt.plot(ts, values, linestyle='-', marker='o')
    plt.xticks(rotation=30)
    plt.savefig(fname, bbox_inches='tight')
    plt.close()


COLORS = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
LINE_MARKERS = ['o', '^', 's', '*', '+', 'x', 'v']
LINE_STYLES = [c + m + '-' for m in LINE_MARKERS for c in COLORS]
CHART_TEXTURES = ["/", "-", "+", "x", "o", ".", "*"]
CHART_STYLES = [c + t for t in CHART_TEXTURES for c in COLORS]


def multiseries_plot(multiseries, fname, cols=7):
    """plot multiple metric (sloccount license) time series --- available from
     `multiseries` as a dictionary mapping series name to list of <timestamp,
    value> paris --- and save it to file `fname`

    """
    logging.debug('generate sloccount plot to %s...' % fname)
    plt.figure()
    plt.yscale('log')

    def by_value((x1, y1), (x2, y2)):
        return cmp(y1, y2)

    styles = cycle(LINE_STYLES)
    for name, series in sorted(six.iteritems(multiseries),
                               cmp=by_value, reverse=True):
        ts, values = _split_series(series)
        if any(values):
            plt.plot(ts, values, next(styles), label=name)

    # plt.legend(bbox_to_anchor=(0., 1.02, 1., .102),
    # plt.legend(bbox_to_anchor=(0, -0.04),
    plt.xticks(rotation=30)
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), mode='expand',
               loc='lower left', ncol=cols,
               prop={'size': 8})

    plt.savefig(fname, bbox_inches='tight')
    plt.close()


def pie_chart(items, fname, ratio=None):
    """plot a pie chart of `items` (i.e slocs, licenses), a dictionary
    which maps a metric to a value. Save the obtained chart to `fname`

    """
    logging.debug('generate sloccount pie chart to %s...' % fname)
    cols = cm.Set1(np.arange(20) / 20.)
    plt.figure()
    keys, values = _split_series(list(six.iteritems(items)))
    modified_keys = ["Other: ", "Other"]
    modified_values = [0]
    for i, value in enumerate(values):
        if value > sum(values) * 2 / 100:
            modified_values.append(value)
            modified_keys.append(keys[i])
        else:
            modified_values[0] = (value + modified_values[0])
            modified_keys[0] = modified_keys[0] + keys[i].replace("_", ' ') \
                + " / "
            if len(modified_keys[0].split('\n')[-1]) > 50:
                modified_keys[0] = modified_keys[0] + "\n"
    # delete trailing /
    modified_keys[0] = modified_keys[0][0:-2]
    plt.pie(modified_values, labels=modified_keys[1:], autopct='%1.1f%%',
            colors=cols)
    if ratio:
        modified_keys[0] += '\n\nPercentage of files with non machine' \
                            ' readable d/copyright files  = ' \
                            + str(int(ratio * 100)) + '%'
    plt.figtext(.02, .02, modified_keys[0])
    plt.savefig(fname)
    plt.close()


def bar_chart(items_per_suite, suites, fname, N, y_label):
    """plot a bar chart of top-`N` languages of the `suites` using the
    sloccount available in `items_per_suite`. Save the chart in `fname`.

    """
    logging.debug('generate sloccount bat chart to %s...' % fname)

    try:
        latest_release = items_per_suite[-2]
    except IndexError:
        if len(items_per_suite) == 1:
            logging.warn('sloc bar chart failed '
                         + 'as only one suite is available')
            return
        else:
            logging.warn('sloc bar chart failed ' +
                         'as there are no suites to plot')
            return
    # Verify N is at most the maximum languages in a suite
    if N >= len(latest_release):
        N = len(latest_release) - 1

    # Generate data
    latest = sorted(list(latest_release.items()),
                    key=operator.itemgetter(1), reverse=True)
    keys = [couple[0] for couple in latest[0:N]]
    important = []
    for key in keys:
        slocs = []
        for i in range(0, len(suites)):
            slocs.append(items_per_suite[i][key]
                         if key in items_per_suite[i].keys() else 0)
        important.append(slocs)
    plt.figure()
    ind = np.arange(len(suites))
    width = 0.33

    styles = cycle(CHART_STYLES)
    c, t = next(styles)
    bar_charts = []
    # Add first language without anything on bottom
    bar_charts.append(plt.bar(ind, important[0], width, color=c, hatch=t))
    # Add the rest of the languages
    for i in range(1, len(keys)):
        c, t = next(styles)
        bar_charts.append(plt.bar(ind, important[i], width,
                                  color=c, hatch=t,
                                  bottom=bottom_sum(important[0:i],
                                                    len(suites))))

    plt.ylabel(y_label)
    plt.xticks(ind + width / 2., (suites), rotation=75)
    plt.legend((p[0] for p in bar_charts),
               (keys), loc='center left', bbox_to_anchor=(1, 0.5))
    plt.savefig(fname, bbox_inches='tight')
    plt.close()


def bottom_sum(items, n):
    """calculate the bottom argument for the bar chart by calculating the
    existing stack sloc available in `items` for a number `n` of suites.
    Return the stack

    """
    b_sum = [0] * n
    for item in items:
        for z, i in enumerate(item):
            b_sum[z] += i
    return b_sum
