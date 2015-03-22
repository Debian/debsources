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

from sqlalchemy import sql

from debsources import db_storage
from debsources import fs_storage
from debsources import hashutil

from debsources.models import Checksum, File


conf = None

MY_NAME = 'checksums'
MY_EXT = '.' + MY_NAME
sums_path = lambda pkgdir: pkgdir + MY_EXT

# maximum number of ctags after which a (bulk) insert is sent to the DB
BULK_FLUSH_THRESHOLD = 100000


def parse_checksums(path):
    """parse sha256 checksums from a file in SHA256SUM(1) format

    i.e. each line is "SHA256  PATH\n"

    yield (sha256, path) pairs
    """
    with open(path) as checksums:
        for line in checksums:
            line = line.rstrip()
            sha256 = line[0:64]
            path = line[66:]
            yield (sha256, path)


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('add-package %s' % pkg)

    sumsfile = sums_path(pkgdir)
    sumsfile_tmp = sumsfile + '.new'

    def emit_checksum(out, relpath, abspath):
        if os.path.islink(abspath) or not os.path.isfile(abspath):
            # Do not checksum symlinks, if they are not dangling / external we
            # will checksum their target anyhow. Do not check special files
            # either; they shouldn't be there per policy, but they might be
            # (and they are in old releases)
            return
        sha256 = hashutil.sha256sum(abspath)
        out.write('%s  %s\n' % (sha256, relpath))

    if 'hooks.fs' in conf['backends']:
        if not os.path.exists(sumsfile):  # compute checksums only if needed
            with open(sumsfile_tmp, 'w') as out:
                for (relpath, abspath) in \
                        fs_storage.walk_pkg_files(pkgdir, file_table):
                    emit_checksum(out, relpath, abspath)
            os.rename(sumsfile_tmp, sumsfile)

    if 'hooks.db' in conf['backends']:
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        insert_q = sql.insert(Checksum.__table__)
        insert_params = []
        if not session.query(Checksum) \
                      .filter_by(package_id=db_package.id) \
                      .first():
            # ASSUMPTION: if *a* checksum of this package has already
            # been added to the db in the past, then *all* of them have,
            # as additions are part of the same transaction
            for (sha256, relpath) in parse_checksums(sumsfile):
                params = {'package_id': db_package.id,
                          'sha256': sha256}
                if file_table:
                    try:
                        file_id = file_table[relpath]
                        params['file_id'] = file_id
                    except KeyError:
                        continue
                else:
                    file_ = session.query(File) \
                                   .filter_by(package_id=db_package.id,
                                              path=relpath) \
                                   .first()
                    if not file_:
                        continue
                    params['file_id'] = file_.id
                insert_params.append(params)
                if len(insert_params) >= BULK_FLUSH_THRESHOLD:
                    session.execute(insert_q, insert_params)
                    session.flush()
                    insert_params = []
            if insert_params:  # source packages shouldn't be empty but...
                session.execute(insert_q, insert_params)
                session.flush()


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('rm-package %s' % pkg)

    if 'hooks.fs' in conf['backends']:
        sumsfile = sums_path(pkgdir)
        if os.path.exists(sumsfile):
            os.unlink(sumsfile)

    if 'hooks.db' in conf['backends']:
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        session.query(Checksum) \
               .filter_by(package_id=db_package.id) \
               .delete()


def init_plugin(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title=MY_NAME)
    debsources['subscribe']('rm-package',  rm_package,  title=MY_NAME)
    debsources['declare_ext'](MY_EXT, MY_NAME)
