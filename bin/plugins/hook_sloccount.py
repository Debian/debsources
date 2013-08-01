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
import re
import subprocess

import dbutils

from models import SlocCount


slocfile_path = lambda pkgdir: pkgdir + '.sloccount'


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


def add_package(session, pkg, pkgdir):
    logging.debug('add-package %s' % pkg)

    slocfile = slocfile_path(pkgdir)
    try:
        cmd = [ 'sloccount', pkgdir ]
        with open(slocfile, 'w') as out:
            subprocess.check_call(cmd, stdout=out, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        if not grep(['^SLOC total is zero,', slocfile]):
            # rationale: sloccount fails when it can't find source code
            raise

    slocs = parse_sloccount(slocfile)
    version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
    assert version is not None
    for (lang, locs) in slocs.iteritems():
        sloccount = session.query(SlocCount) \
                           .filter_by(sourceversion_id=version.id,
                                     language=lang,
                                     count=locs) \
                          .first()
        if sloccount:
            break # ASSUMPTION: if *a* loc count of this package has already
                  # been added to the db in the past, then *all* of them have,
                  # as additions are part of the same transaction
        sloccount = SlocCount(version, lang, locs)
        session.add(sloccount)


def rm_package(session, pkg, pkgdir):
    logging.debug('rm-package %s' % pkg)

    # note: sloccount data in db will be removed by ON DELETE CASCADE
    slocfile = slocfile_path(pkgdir)
    if os.path.exists(slocfile):
        os.unlink(slocfile)


def debsources_main(debsources):
    debsources['subscribe']('add-package', add_package, title='sloccount')
    debsources['subscribe']('rm-package',  rm_package,  title='sloccount')
