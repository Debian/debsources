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


metricsfile_path = lambda pkgdir: pkgdir + '.stats'


def add_package(session, pkg, pkgdir):
    logging.debug('add-package %s' % pkg)

    metricsfile = metricsfile_path(pkgdir)
    cmd = [ 'du', '--summarize', pkgdir ]
    metric_type = 'size'
    metric_value = int(subprocess.check_output(cmd).split()[0])
    with open(metricsfile, 'w') as out:
        out.write('%s\t%d\n' % (metric_type, metric_value))

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
    logging.debug('rm-package %s' % pkg)

    metricsfile = metricsfile_path(pkgdir)
    if os.path.exists(metricsfile):
        os.unlink(metricsfile)

    version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
    session.query(Metric) \
           .filter_by(sourceversion_id=version.id) \
           .delete()


def debsources_main(debsources):
    debsources['subscribe']('add-package', add_package, title='metrics')
    debsources['subscribe']('rm-package',  rm_package,  title='metrics')
