# Copyright (C) 2013-2015  The Debsources developers <info@sources.debian.net>.
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
import os
import subprocess

from sqlalchemy import sql

from debsources import db_storage

from debsources.models import Ctag, File
from debsources.consts import MAX_KEY_LENGTH


conf = None

CTAGS_FLAGS = ['--recurse',
               '--excmd=number',
               '--fields=+lnz',
               # '--extra=+q',
               '--sort=no',
               '--links=no']

MY_NAME = 'ctags'
MY_EXT = '.' + MY_NAME


def ctags_path(pkgdir):
    return pkgdir + MY_EXT

# maximum number of ctags after which a (bulk) insert is sent to the DB
BULK_FLUSH_THRESHOLD = 20000

# maximum number of detailed warnings for malformed tags that will be emitted.
# used to avoid flooding logs
BAD_TAGS_THRESHOLD = 5


def parse_ctags(path):
    """parse exuberant ctags tags file

    for each tag yield a tag dictionary::

      { 'tag':  'TAG_NAME',
        'path': 'PATH/WITH/IN/PACKAGE',
        'line': LINE_NUMBER, # int
        'kind': 'TAG_KIND', # 1 letter
        'language': 'TAG_LANGUAGE',
      }
    """
    def parse_tag(line):
        tag = {'kind': None, 'line': None, 'language': None}
        # initialize with extension fields which are not guaranteed to exist

        fields = line.rstrip().split('\t')
        # will fail when encountering encoding
        # issues; that is intended
        tag['tag'] = fields[0].decode()
        tag['path'] = fields[1]
        # note: ignore fields[2], ex_cmd

        for ext in fields[3:]:  # parse extension fields
            k, v = ext.split(':', 1)  # caution: "typeref:struct:__RAW_R_INFO"
            if k == 'kind':
                tag['kind'] = v
            elif k == 'line':
                tag['line'] = int(v)
            elif k == 'language':
                tag['language'] = v.lower()
            else:
                pass  # ignore other fields

        assert tag['line'] is not None
        assert len(tag['tag']) <= MAX_KEY_LENGTH
        return tag

    with open(path) as ctags:
        bad_tags = 0
        for line in ctags:
            # e.g. 'music\tsound.c\t13;"\tkind:v\tline:13\tlanguage:C\tfile:\n'
            # see CTAGS(1), section "TAG FILE FORMAT"
            if line.startswith('!_TAG'):  # skip ctags metadata
                continue
            try:
                yield parse_tag(line)
            except:
                bad_tags += 1
                if bad_tags <= BAD_TAGS_THRESHOLD:
                    logging.warn('ignore malformed tag "%s"' % line.rstrip())
        if bad_tags > BAD_TAGS_THRESHOLD:
            logging.warn('%d extra malformed tag(s) ignored' %
                         (bad_tags - BAD_TAGS_THRESHOLD))


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('add-package %s' % pkg)

    ctagsfile = ctags_path(pkgdir)
    ctagsfile_tmp = ctagsfile + '.new'

    if 'hooks.fs' in conf['backends']:
        if not os.path.exists(ctagsfile):  # extract tags only if needed
            cmd = ['ctags'] + CTAGS_FLAGS + ['-o', ctagsfile_tmp]
            # ASSUMPTION: will be run under pkgdir as CWD, which is needed to
            # get relative paths right. The assumption is enforced by the
            # updater
            with open(os.devnull, 'w') as null:
                subprocess.check_call(cmd, stderr=null)
            os.rename(ctagsfile_tmp, ctagsfile)

    if 'hooks.db' in conf['backends']:
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        # poor man's cache for last <relpath, file_id>;
        # rely on the fact that ctags file are path-sorted
        curfile = {None: None}
        insert_q = sql.insert(Ctag.__table__)
        insert_params = []
        if not session.query(Ctag).filter_by(package_id=db_package.id).first():
            # ASSUMPTION: if *a* ctag of this package has already been added to
            # the db in the past, then *all* of them have, as additions are
            # part of the same transaction
            for tag in parse_ctags(ctagsfile):
                params = ({'package_id': db_package.id,
                           'tag': tag['tag'],
                           # 'file_id': 	# will be filled below
                           'line': tag['line'],
                           'kind': tag['kind'],
                           'language': tag['language']})
                relpath = tag['path']
                if file_table:
                    try:
                        params['file_id'] = file_table[relpath]
                    except KeyError:
                        continue
                else:
                    try:
                        params['file_id'] = curfile[relpath]
                    except KeyError:
                        file_ = session.query(File) \
                                       .filter_by(package_id=db_package.id,
                                                  path=relpath) \
                                       .first()
                        if not file_:
                            continue
                        curfile = {relpath: file_.id}
                        params['file_id'] = file_.id
                insert_params.append(params)
                if len(insert_params) >= BULK_FLUSH_THRESHOLD:
                    session.execute(insert_q, insert_params)
                    session.flush()
                    insert_params = []
            if insert_params:  # might be empty if there are no ctags at all!
                session.execute(insert_q, insert_params)
                session.flush()


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('rm-package %s' % pkg)

    if 'hooks.fs' in conf['backends']:
        ctagsfile = ctags_path(pkgdir)
        if os.path.exists(ctagsfile):
            os.unlink(ctagsfile)

    if 'hooks.db' in conf['backends']:
        db_package = db_storage.lookup_package(session, pkg['package'],
                                               pkg['version'])
        session.query(Ctag) \
               .filter_by(package_id=db_package.id) \
               .delete()


def init_plugin(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title=MY_NAME)
    debsources['subscribe']('rm-package',  rm_package,  title=MY_NAME)
    debsources['declare_ext'](MY_EXT, MY_NAME)
