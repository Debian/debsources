# Copyright (C) 2013-2014  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import

import logging
import os
import re
import subprocess

import six

from debsources import db_storage
from debsources.models import SlocCount


conf = None

SLOCCOUNT_FLAGS = ['--addlangall']

MY_NAME = 'sloccount'
MY_EXT = '.' + MY_NAME
slocfile_path = lambda pkgdir: pkgdir + MY_EXT


def grep(args):
    """boolean wrapper around GREP(1)
    """
    rc = None
    with open(os.devnull, 'w') as null:
        rc = subprocess.call(['grep'] + args, stdout=null, stderr=null)
    return (rc == 0)


SLOC_TBL_HEADER = re.compile('^Totals grouped by language')
SLOC_TBL_FOOTER = re.compile('^\s*$')
SLOC_TBL_LINE = re.compile('^(?P<lang>[^:]+):\s+(?P<locs>\d+)')


def parse_sloccount(path):
    """parse SLOCCOUNT(1) output and return a mapping from languages to locs

    language names are the same returned by sloccount, normalized to lowercase
    """
    slocs = {}
    in_table = False
    with open(path) as sloccount:
        for line in sloccount:
            if in_table:
                m = re.match(SLOC_TBL_FOOTER, line)
                if m:
                    break
                m = re.match(SLOC_TBL_LINE, line)
                if m:
                    slocs[m.group('lang')] = int(m.group('locs'))
            else:
                m = re.match(SLOC_TBL_HEADER, line)
                if m:
                    in_table = True
    return slocs


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('add-package %s' % pkg)

    slocfile = slocfile_path(pkgdir)
    slocfile_tmp = slocfile + '.new'

    if 'hooks.fs' in conf['backends']:
        if not os.path.exists(slocfile):  # run sloccount only if needed
            try:
                cmd = ['sloccount'] + SLOCCOUNT_FLAGS + [pkgdir]
                with open(slocfile_tmp, 'w') as out:
                    subprocess.check_call(cmd, stdout=out,
                                          stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError:
                if not grep(['^SLOC total is zero,', slocfile_tmp]):
                    # rationale: sloccount fails when it can't find source code
                    raise
            finally:
                os.rename(slocfile_tmp, slocfile)

    if 'hooks.db' in conf['backends']:
        slocs = parse_sloccount(slocfile)
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        if not session.query(SlocCount).filter_by(package_id=db_package.id)\
                                       .first():
            # ASSUMPTION: if *a* loc count of this package has already been
            # added to the db in the past, then *all* of them have, as
            # additions are part of the same transaction
            for (lang, locs) in six.iteritems(slocs):
                sloccount = SlocCount(db_package, lang, locs)
                session.add(sloccount)


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('rm-package %s' % pkg)

    if 'hooks.fs' in conf['backends']:
        slocfile = slocfile_path(pkgdir)
        if os.path.exists(slocfile):
            os.unlink(slocfile)

    if 'hooks.db' in conf['backends']:
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        session.query(SlocCount) \
               .filter_by(package_id=db_package.id) \
               .delete()


def init_plugin(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title='sloccount')
    debsources['subscribe']('rm-package',  rm_package,  title='sloccount')
    debsources['declare_ext'](MY_EXT, MY_NAME)
