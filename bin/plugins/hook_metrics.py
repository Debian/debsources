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
import subprocess

import dbutils

from models import Metric


conf = None

MY_NAME = 'metrics'
MY_EXT = '.stats'
metricsfile_path = lambda pkgdir: pkgdir + MY_EXT


def parse_metrics(path):
    metrics = {}
    with open(path) as metricsfile:
        for line in metricsfile:
            metric, value = line.split()
            metrics[metric] = int(value)
    return metrics


def add_package(session, pkg, pkgdir):
    global conf
    logging.debug('add-package %s' % pkg)

    metric_type = 'size'
    metric_value = None
    metricsfile = metricsfile_path(pkgdir)
    metricsfile_tmp = metricsfile + '.new'

    if 'hooks.fs' in conf['passes']:
        if not os.path.exists(metricsfile):	# run du only if needed
            cmd = [ 'du', '--summarize', pkgdir ]
            metric_value = int(subprocess.check_output(cmd).split()[0])
            with open(metricsfile_tmp, 'w') as out:
                out.write('%s\t%d\n' % (metric_type, metric_value))
            os.rename(metricsfile_tmp, metricsfile)

    if 'hooks.db' in conf['passes']:
        if metric_value is None:
            # hooks.db is enabled but hooks.fs is not, so we don't have a
            # metric_value handy. Parse it from metrics file, hoping it exists
            # from previous runs...
            metric_value = parse_metrics(metricsfile)[metric_type]

        version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
        metric = session.query(Metric) \
                        .filter_by(sourceversion_id=version.id,
                                   metric=metric_type,
                                   value=metric_value) \
                        .first()
        if not metric:
            metric = Metric(version, metric_type, metric_value)
            session.add(metric)


def rm_package(session, pkg, pkgdir):
    global conf
    logging.debug('rm-package %s' % pkg)

    if 'hooks.fs' in conf['passes']:
        metricsfile = metricsfile_path(pkgdir)
        if os.path.exists(metricsfile):
            os.unlink(metricsfile)

    if 'hooks.db' in conf['passes']:
        version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
        session.query(Metric) \
               .filter_by(sourceversion_id=version.id) \
               .delete()


def debsources_main(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title=MY_NAME)
    debsources['subscribe']('rm-package',  rm_package,  title=MY_NAME)
    debsources['declare_ext'](MY_EXT, MY_NAME)
