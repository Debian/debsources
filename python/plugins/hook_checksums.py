# Copyright (C) 2013-2014  Stefano Zacchiroli <zack@upsilon.cc>
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

from sqlalchemy import sql

import dbutils
import fs_storage
import hashutil

from models import Checksum, File


conf = None

MY_NAME = 'checksums'
MY_EXT = '.' + MY_NAME
sums_path = lambda pkgdir: pkgdir + MY_EXT


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
        if os.path.islink(abspath):
            # do not checksum symlinks, if they are not dangling / external we
            # will checksum their target anyhow
            return
        sha256 = hashutil.sha256sum(abspath)
        out.write('%s  %s\n' % (sha256, relpath))

    if 'hooks.fs' in conf['passes']:
        if not os.path.exists(sumsfile): # compute checksums only if needed
            with open(sumsfile_tmp, 'w') as out:
                if file_table:
                    for relpath in file_table.iterkeys():
                        abspath = os.path.join(pkgdir, relpath)
                        emit_checksum(out, relpath, abspath)
                else:
                    for abspath in fs_storage.walk_pkg_files(pkgdir):
                        relpath = os.path.relpath(abspath, pkgdir)
                        emit_checksum(out, relpath, abspath)
            os.rename(sumsfile_tmp, sumsfile)

    if 'hooks.db' in conf['passes']:
        version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
        insert_q = sql.insert(Checksum)
        insert_params = []
        if not session.query(Checksum).filter_by(version_id=version.id).first():
            # ASSUMPTION: if *a* checksum of this package has already
            # been added to the db in the past, then *all* of them have,
            # as additions are part of the same transaction
            for (sha256, relpath) in parse_checksums(sumsfile):
                params = {'version_id': version.id,
                          'sha256': sha256,
                      }
                if file_table:
                    checksum = Checksum(version, file_table[relpath], sha256)
                    params['file_id'] = file_table[relpath]
                else:
                    file_ = session.query(File).filter_by(version_id=version.id,
                                                          path=relpath).first()
                    if not file_:
                        continue
                    params['file_id'] = file_.id
                insert_params.append(params)
            if insert_params:	# source packages shouldn't be empty but...
                session.execute(insert_q, insert_params)


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('rm-package %s' % pkg)

    if 'hooks.fs' in conf['passes']:
        sumsfile = sums_path(pkgdir)
        if os.path.exists(sumsfile):
            os.unlink(sumsfile)

    if 'hooks.db' in conf['passes']:
        version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
        session.query(Checksum) \
               .filter_by(version_id=version.id) \
               .delete()


def init_plugin(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title=MY_NAME)
    debsources['subscribe']('rm-package',  rm_package,  title=MY_NAME)
    debsources['declare_ext'](MY_EXT, MY_NAME)
