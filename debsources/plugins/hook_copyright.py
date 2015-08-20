# Copyright (C) 2015  The Debsources developers <info@sources.debian.net>.
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

import io
import logging
import os

from debsources import db_storage, fs_storage
from debsources.models import FileCopyright, File
from debsources import license_helper as helper

conf = None

MY_NAME = 'copyright'
MY_EXT = '.' + MY_NAME
license_path = lambda pkgdir: pkgdir + MY_EXT


def parse_license_file(path):
    license_list = []
    with open(path) as licenses:
        for line in licenses:
            fields = line.rstrip().split('\t')
            license_list.append((fields[0], fields[1]))
    return license_list


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('add-package %s' % pkg)

    license_file = license_path(pkgdir)
    license_file_tmp = license_file + '.new'

    def emit_license(out, session, package, version, relpath, pkgdir):
        """ Retrieve license of the file. We use `relpath` as we want the path
            inside the package directory which is used in the d/copyright files
            paragraphs
        """
        # join path for debian/copyright file as we are already in the sources
        # directory.
        synopsis = helper.get_license(session, package, version, relpath,
                                      os.path.join(pkgdir, 'debian/copyright'))
        if synopsis is not None:
            s = '%s\t%s\n' % (synopsis, relpath.decode('utf-8'))
            out.write(s)

    if 'hooks.fs' in conf['backends']:
        if not os.path.exists(license_file):  # run license only if needed
            with io.open(license_file_tmp, 'w', encoding='utf-8') as out:
                for (relpath, abspath) in \
                        fs_storage.walk_pkg_files(pkgdir, file_table):
                    emit_license(out, session, pkg['package'], pkg['version'],
                                 relpath, pkgdir)
            os.rename(license_file_tmp, license_file)

    if 'hooks.db' in conf['backends']:
        licenses = parse_license_file(license_file)
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        session.query(FileCopyright) \
               .join(File) \
               .filter(File.package_id == db_package.id)
        if not session.query(FileCopyright).join(File)\
                      .filter(File.package_id == db_package.id).first():
            # ASSUMPTION: if *a* license of this package has already been
            # added to the db in the past, then *all* of them have, as
            # additions are part of the same transaction
            for (synopsis, path) in licenses:
                if file_table:
                    try:
                        file_id = file_table[path]
                    except KeyError:
                        continue
                else:
                    file_ = session.query(File) \
                                   .filter_by(package_id=db_package.id,
                                              path=path) \
                                   .first()
                    if not file_:
                        continue
                    file_id = file_.id
                license = FileCopyright(file_id, 'debian', synopsis)
                session.add(license)


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('rm-package %s' % pkg)

    if 'hooks.fs' in conf['backends']:
        licensefile = license_path(pkgdir)
        if os.path.exists(licensefile):
            os.unlink(licensefile)

    if 'hooks.db' in conf['backends']:
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        files = (session.query(FileCopyright.id)
                 .join(File)
                 .filter(File.package_id == db_package.id)).all()
        for f in files:
            session.query(FileCopyright) \
                   .filter(FileCopyright.id == f).delete()


def init_plugin(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title=MY_NAME)
    debsources['subscribe']('rm-package', rm_package, title=MY_NAME)
    debsources['declare_ext'](MY_EXT, MY_NAME)
