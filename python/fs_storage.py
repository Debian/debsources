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
import shutil
import signal
import subprocess

from subprocess_workaround import subprocess_setup


def extract_package(pkg, destdir):
    """extract a package to the FS storage
    """
    logging.debug('extract %s...' % pkg)
    parentdir = os.path.dirname(destdir)
    if not os.path.isdir(parentdir):
        os.makedirs(parentdir)
    if os.path.isdir(destdir):	# remove stale dir, dpkg-source doesn't clobber
        shutil.rmtree(str(destdir))
    dsc = pkg.dsc_path()
    cmd = ['dpkg-source', '--no-copy', '--no-check',
           '-x', dsc, destdir ]
    logfile = destdir + '.log'
    donefile = destdir + '.done'
    with open(logfile, 'w') as log:
        subprocess.check_call(cmd, stdout=log, stderr=subprocess.STDOUT,
                              preexec_fn=subprocess_setup)
    open(donefile, 'w').close()


def remove_package(pkg, destdir):
    """dispose of a package from the Debsources file system storage
    """
    if os.path.exists(destdir):
        shutil.rmtree(str(destdir))
    for meta in ['log', 'done']:
        fname = destdir + '.' + meta
        if os.path.exists(fname):
            os.unlink(fname)
    try:
        os.removedirs(os.path.dirname(destdir))
    except OSError:
        pass	# parent dir is likely non empty, due to other package versions


def walk(sources_dir, test=None):
    """iterate over FS storage files

    yield paths to either package directories or metadata files (e.g. .stats,
    .sloccount, etc.

    if test is given then it should be callable predicate; only paths on which
    it returns True will be returned
    """
    for cwd, dirs, files in os.walk(sources_dir):
        cwd_rel = os.path.relpath(cwd, sources_dir)
        depth = len(cwd_rel.split('/'))
        if depth == 3:
            # e.g. (dir)  contrib/v/vor/0.5.5-2
            # e.g. (file) contrib/v/vor/0.5.5-2.checksums
            for item in files + dirs:
                path = os.path.join(cwd, item)
                if test is None or test(path):
                    yield path
            del(dirs[:])	# stop recursion


def walk_pkg_files(pkgdir, file_table=None):
    """walk through the source files in pkgdir, yielding a pair <relpath, abspath>
    a time. `relpath` is a path relative to `pkgdir`, whereas `abspath` is an
    absolute path (as long as `pkgdir` is absolute as well; otherwise it is "as
    absolute" as `pkgdir` is)

    """
    if isinstance(pkgdir, unicode):
        # dumb down pkgdir to byte string. Whereas pkgdir comes from Sources
        # and hence is ASCII clean, the paths that os.walk() will encounter
        # might not even be UTF-8 clean. Using str() we ensure that path
        # operations will happen between raw strings, avoding encoding issues.
        pkgdir = str(pkgdir)
    if file_table:
        for relpath in file_table.iterkeys():
            abspath = os.path.join(pkgdir, relpath)
            yield (relpath, abspath)
    else:
        for root, dirs, files in os.walk(pkgdir):
            for f in files:
                abspath = os.path.join(root, f)
                relpath = os.path.relpath(abspath, pkgdir)
                yield (relpath, abspath)


def parse_path(fname):
    """parse a path pointing into the FS storage

    returns a dictionary like

    { 'package': NAME,
      'version': VERSION,
      'ext':    '.checksums',
    }

    where the ext key is None for package directories
    """
    steps = fname.split('/')
    path = { 'package': steps[-2],
             'version': steps[-1],
             'ext':     None }
    if os.path.isdir(fname):	# e.g. contrib/v/vor/0.5.5-2
        pass
    elif os.path.isfile(fname):	# e.g. contrib/v/vor/0.5.5-2.checksums
        (base, ext) = os.path.splitext(path['version'])
        path['version'] = base
        path['ext'] = ext
    else:
        assert False
    return path


def rm_file(pkgdir, relpath):
    """remove file `relpath` from package directory `pkgdir`

    """
    path = os.path.join(pkgdir, relpath)
    if os.path.exists(path):
        os.unlink(path)
    else:
        logging.warning('cannot remove non existing file %s' % path)
