# Copyright (C) 2013  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING

from __future__ import absolute_import

import glob
import logging
import os
import shutil
import subprocess
from pathlib import Path

from debsources.consts import DPKG_EXTRACT_UMASK
from debsources.subprocess_workaround import subprocess_setup


def extract_package(pkg, destdir: Path):
    """extract a package to the FS storage
    """
    def preexec_fn():
        subprocess_setup()
        os.umask(DPKG_EXTRACT_UMASK)

    logging.debug('extract %s...' % pkg)
    parentdir = destdir.parent
    if not parentdir.is_dir():
        os.makedirs(parentdir)
    if destdir.is_dir():  # remove stale dir, dpkg-source doesn't clobber
        shutil.rmtree(destdir)
    dsc = pkg.dsc_path()
    cmd = ['dpkg-source', '--no-copy', '--no-check', '-x', str(dsc), str(destdir)]
    logfile = Path(str(destdir) + '.log')
    donefile = Path(str(destdir) + '.done')
    with logfile.open('w') as log:
        subprocess.check_call(cmd, stdout=log, stderr=subprocess.STDOUT,
                              preexec_fn=preexec_fn)
    donefile.touch()


def remove_package(pkg, destdir: Path):
    """dispose of a package from the Debsources file system storage
    """
    if destdir.exists():
        shutil.rmtree(str(destdir))
    for meta in ['log', 'done']:
        fname = Path(str(destdir) + '.' + meta)
        if fname.exists():
            fname.unlink()
    try:
        os.removedirs(destdir.parent)
    except OSError:
        pass  # parent dir is likely non empty, due to other package versions


def walk(sources_dir: Path, test=None):
    """iterate over FS storage files

    yield paths to either package directories or metadata files (e.g. .stats,
    .sloccount, etc.

    if test is given then it should be callable predicate; only paths on which
    it returns True will be returned
    """
    for item in glob.iglob(f'{str(sources_dir)}/*/*/*/*'):
        # e.g. (dir)  contrib/v/vor/0.5.5-2
        # e.g. (file) contrib/v/vor/0.5.5-2.checksums
        item = Path(item)
        if test is None or test(item):
            yield item


def walk_pkg_files(pkgdir: Path):
    """walk the source files in pkgdir, yielding pairs <relpath, abspath>.
    `relpath` is a path relative to `pkgdir`, whereas `abspath` is an absolute
    path (as long as `pkgdir` is absolute as well; otherwise it is "as
    absolute" as `pkgdir` is)
    """
    for root, dirs, files in os.walk(pkgdir):
        for f in files:
            abspath = Path(root) / f
            relpath = abspath.relative_to(pkgdir)
            yield (relpath, abspath)


def parse_path(fname: Path):
    """parse a path pointing into the FS storage

    returns a dictionary like

    { 'package': NAME,
      'version': VERSION,
      'ext':    '.checksums',
    }

    where the ext key is None for package directories
    """
    steps = fname.parts
    parsed = {'package': steps[-2],
              'version': steps[-1],
              'ext':     None}
    if fname.is_dir():  # e.g. contrib/v/vor/0.5.5-2
        pass
    elif fname.is_file():  # e.g. contrib/v/vor/0.5.5-2.checksums
        *base, ext = parsed['version'].split('.')
        parsed['version'] = '.'.join(base)
        parsed['ext'] = f".{ext}"
    else:
        raise Exception(
            f"Trying to parse a path that is not a file or a folder: {fname}")

    return parsed


def rm_file(pkgdir: Path, relpath: Path):
    """remove file `relpath` from package directory `pkgdir`
    """
    path = pkgdir / relpath
    if path.exists():
        path.unlink()
    else:
        logging.warning('cannot remove non existing file %s' % path)
