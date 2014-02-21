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


def plot(series, fname):
    ts, values = [], []
    for t, value in series:
        if value is not None:
            ts.append(t)
            values.append(value)

    plt.figure()
    plt.plot(ts, values, linestyle='-', marker='o')
    plt.savefig(fname)
    plt.close()

    # with open(fname, 'w') as f:
    #     for (ts, v) in series:
    #         if (v is None):
    #             v = "None"
    #         f.write('%s\t%s\n' % (ts, v))
