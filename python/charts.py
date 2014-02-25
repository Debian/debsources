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

import matplotlib.pyplot as plt

from itertools import cycle


def _split_series(series):
    """splite a time `series` (list of <x,y> points) into two lists --- one of x
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
    ts, values = _split_series(series)

    plt.figure()
    plt.plot(ts, values, linestyle='-', marker='o')
    plt.savefig(fname)
    plt.close()


LINE_COLORS =  ['b', 'g', 'r', 'c', 'm', 'y', 'k']
LINE_MARKERS = ['o', '^', 's', '*', '+', 'x', 'v']
LINE_STYLES =  [ c + m + '-' for m in LINE_MARKERS for c in LINE_COLORS ]


def sloc_plot(multiseries, fname):
    """plot multiple sloccount time series --- available from `multiseries` as a
    dictionary mapping series name to list of <timestamp, value> paris --- and
    save it to file `fname`

    """
    plt.figure()
    plt.yscale('log')

    by_value = lambda (x1, y1), (x2, y2): cmp(y1, y2)

    styles = cycle(LINE_STYLES)
    for name, series in sorted(multiseries.iteritems(),
                               cmp=by_value, reverse=True):
        ts, values = _split_series(series)
        if filter(bool, values): # at least one value is != None and != 0
            plt.plot(ts, values, styles.next(), label=name)

    # plt.legend(bbox_to_anchor=(0., 1.02, 1., .102),
    # plt.legend(bbox_to_anchor=(0, -0.04),
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), mode='expand',
               loc='lower left', ncol=7,
               prop={'size': 8})

    plt.savefig(fname, bbox_inches='tight')
    plt.close()


def sloc_pie(slocs, fname):
   """plot a pie chart of sloccount in `slocs`, a dictionary which maps language
   names to slocs. Save the obtained chart to `fname`

   """
   plt.figure()
   langs, slocs = _split_series(list(slocs.iteritems()))
   plt.pie(slocs, labels=langs, autopct='%1.1f%%')
   plt.savefig(fname)
   plt.close()
