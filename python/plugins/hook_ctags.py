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
import subprocess

import dbutils

from models import Ctag, File, MAX_KEY_LENGTH


conf = None

CTAGS_FLAGS = [ '--recurse',
                '--excmd=number',
                '--fields=+lnz',
                '--sort=no',
]
                
MY_NAME = 'ctags'
MY_EXT = '.' + MY_NAME
ctags_path = lambda pkgdir: pkgdir + MY_EXT


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
        tag = { 'kind': None, 'line': None, 'language': None }
        # initialize with extension fields which are not guaranteed to exist

        fields = line.rstrip().split('\t')
        tag['tag'] = fields[0].decode()	# will fail when encountering encoding issues;
					# that is intended
        tag['path'] = fields[1]
        # note: ignore fields[2], ex_cmd

        for ext in fields[3:]:	# parse extension fields
            k, v = ext.split(':', 1) # caution: "typeref:struct:__RAW_READ_INFO"
            if k == 'kind':
                tag['kind'] = v
            elif k == 'line':
                tag['line'] = int(v)
            elif k == 'language':
                tag['language'] = v.lower()
            else:
                pass	# ignore other fields

        assert tag['line'] is not None
        assert len(tag['tag']) <= MAX_KEY_LENGTH
        return tag

    with open(path) as ctags:
        for line in ctags:
            # e.g. 'music\tsound.c\t13;"\tkind:v\tline:13\tlanguage:C\tfile:\n'
            # see CTAGS(1), section "TAG FILE FORMAT"
            if line.startswith('!_TAG'):	# skip ctags metadata
                continue
            try:
                yield parse_tag(line)
            except:
                logging.warn('ignore malformed tag "%s"' % line.rstrip())


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('add-package %s' % pkg)

    ctagsfile = ctags_path(pkgdir)
    ctagsfile_tmp = ctagsfile + '.new'

    if 'hooks.fs' in conf['passes']:
        if not os.path.exists(ctagsfile): # extract tags only if needed
            workdir = os.getcwd()
            try:
                cmd = [ 'ctags' ] + CTAGS_FLAGS + [ '-f', '-' ]
                os.chdir(pkgdir) # execute in pkgdir to get relative paths right
                with open(ctagsfile_tmp, 'w') as out,\
                     open(os.devnull, 'w') as null:
                    subprocess.check_call(cmd, stdout=out, stderr=null)
                os.rename(ctagsfile_tmp, ctagsfile)
            finally:
                os.chdir(workdir)

    if 'hooks.db' in conf['passes']:
        version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
        curfile = {None: None}	# poor man's cache for last <relpath, File>;
                             # rely on the fact that ctags file are path-sorted
        if not session.query(Ctag).filter_by(version_id=version.id).first():
            # ASSUMPTION: if *a* cta of this package has already been added to
            # the db in the past, then *all* of them have, as additions are
            # part of the same transaction
            for tag in parse_ctags(ctagsfile):
                relpath = tag['path']
                if file_table:
                    ctag = Ctag(version, tag['tag'], file_table[relpath],
                                tag['line'], tag['kind'], tag['language'])
                    session.add(ctag)
                else:
                    try:
                        file_ = curfile[relpath]
                    except KeyError:
                        file_ = session.query(File).filter_by(version_id=version.id,
                                                              path=relpath).first()
                        curfile = { relpath: file_ }
                    if file_:
                        ctag = Ctag(version, tag['tag'], file_.id, tag['line'],
                                    tag['kind'], tag['language'])
                        session.add(ctag)


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug('rm-package %s' % pkg)

    if 'hooks.fs' in conf['passes']:
        ctagsfile = ctags_path(pkgdir)
        if os.path.exists(ctagsfile):
            os.unlink(ctagsfile)

    if 'hooks.db' in conf['passes']:
        version = dbutils.lookup_version(session, pkg['package'], pkg['version'])
        session.query(Ctag) \
               .filter_by(version_id=version.id) \
               .delete()


def init_plugin(debsources):
    global conf
    conf = debsources['config']
    debsources['subscribe']('add-package', add_package, title=MY_NAME)
    debsources['subscribe']('rm-package',  rm_package,  title=MY_NAME)
    debsources['declare_ext'](MY_EXT, MY_NAME)
