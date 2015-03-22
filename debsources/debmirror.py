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

from debian import deb822
from debian.debian_support import version_compare


class SourcePackage(deb822.Sources):
    """Debian source package, as it appears in a source mirror
    """

    @classmethod
    def from_db_model(cls, db_package):
        """build a (mock) SourcePackage object from a models.Package instance

        note that the built object will not contain all the needed source
        package information, but only those that can be reconstructed using
        information available in the Debsources db.  That, however, should be
        enough for the purposes of Debsources' needs.

        """
        meta = {}
        meta['package'] = db_package.name.name
        meta['version'] = db_package.version
        meta['section'] = db_package.area
        return cls(meta)

    # override deb822's __eq__, as in source package land we can rely on
    # <package, version> pair uniqueness
    def __eq__(self, other):
        """equality based on <package, version> paris only
        """
        if self['package'] != other['package']:
            return False
        if self['version'] != other['version']:
            return False
        return True

    def __cmp__(self, other):
        """comparison based on <package, version> pairs only
        """
        cmp1 = cmp(self['package'], other['package'])
        if cmp1:  # 'package' key is enough to discriminate
            return cmp1
        return version_compare(self['version'], other['version'])

    def __hash__(self):
        """compute hash based on <package, version> pair only
        """
        return hash((self['package'], self['version']))

    def __str__(self):
        """package/version representation of a package
        """
        return "%s/%s" % (self['package'], self['version'])

    __repr__ = __str__
    __unicode__ = __str__

    def archive_area(self):
        """return package are in the debian achive

        one of: main, contrib, non-free. Return `None` if the archive area
        cannot be figured out

        """
        area = None
        try:
            sec = self['section']
            if sec.startswith('contrib'):
                area = 'contrib'
            elif sec.startswith('non-free'):
                area = 'non-free'
            else:
                area = 'main'
        except KeyError:  # section not found, might happen in some old
                # buggy packages; try an heuristic
            try:
                directory = self['directory']
                steps = directory.split('/')
                if 'non-free' in steps:
                    area = 'non-free'
                elif 'contrib' in steps:
                    area = 'contrib'
                else:
                    area = 'main'
                logging.warn('guessed archive area %s for package %s'
                             % (area, self))
            except KeyError:
                area = None

        return area

    @staticmethod
    def pkg_prefix(pkgname):
        """compute package prefix in the pool structure, for pkgname

        same as prefix(), but static method, used to factorize the prefix
        computation logic throughout Debsources

        """
        if pkgname.startswith('lib'):
            prefix = pkgname[:4]
        else:
            prefix = pkgname[:1]
        return prefix.lower()

    def prefix(self):
        """compute package prefix in the pool structure

        e.g.: 1st character of package name or "lib" + 1st char, depending on
        the package
        """
        return self.pkg_prefix(self['package'])

    def dsc_path(self):
        """return (absolute) path to .dsc file for this package
        """
        dsc = filter(lambda f: f['name'].endswith('.dsc'),
                     self['files'])[0]['name']
        return os.path.join(self['x-debsources-mirror-root'],
                            self['directory'], dsc)

    def extraction_dir(self, basedir=None):
        """return package extraction dir, relative to debsources sources_dir

        If given, prepend basedir path to the generated path. Return `None` if
        we can't figure out where to extract the package to

        """
        area = self.archive_area()
        if area is None:
            return None

        steps = [area,
                 self.prefix(),
                 self['package'],
                 self['version']]
        if basedir:
            steps.insert(0, basedir)
        return os.path.join(*steps)


class SourceMirror(object):
    """Handle for a local Debian source mirror
    """

    def __init__(self, path):
        """create a handle to a local source mirror rooted at path
        """
        self.mirror_root = path
        self._suites = None    # dict: suite name -> [<package, version>]
        self._packages = None  # set(<package, version>)
        self._dists_dir = os.path.join(path, 'dists')

    @property
    def suites(self):
        """return a mapping from suite names to <package, version> pairs

        Note: for efficient use, this property is best accessed after having
        used the ls() method
        """
        if self._suites is None:
            for pkg in self.ls():
                pass  # hack: rely on ls' side-effects to populate suites
        assert self._suites is not None
        return self._suites

    @property
    def packages(self):
        """return the mirror packages as a set of <package, version> paris

        Note: for efficient use, this property is best accessed after having
        used the ls() method
        """
        if self._packages is None:
            for pkg in self.ls():
                pass  # hack: rely on ls' side-effects to populate _packages
        assert self._packages is not None
        return self._packages

    def __find_Sources_gz(self):
        """Find Sources.gz entries contained in the mirror

        return them as <suite, path> pairs
        """
        for root, dirs, files in os.walk(self._dists_dir):
            src_indexes = [os.path.join(root, file)
                           for file in files
                           if file == "Sources.gz"]
            for f in src_indexes:
                steps = f.split('/')
                suite = steps[-4]  # wheezy, jessie, sid, ...
                yield suite, f

    def pkg_prefixes(self):
        """Return the list of relevant package prefixes

        takes into account Debian convention, e.g. most packages prefix to
        their first letter, except libraries that prefix to libX

        """
        pool_dir = os.path.join(self.mirror_root, 'pool')
        prefixes = set()
        for pool_subdir in os.listdir(pool_dir):
            # make it absolute
            pool_subdir = os.path.join(pool_dir, pool_subdir)
            for entry in os.listdir(pool_subdir):
                entry = os.path.join(pool_subdir, entry)
                if os.path.isdir(entry):
                    prefixes.add(os.path.relpath(entry, pool_subdir))
        return sorted(list(prefixes))

    def ls(self, suite=None):
        """List SourcePackages instances of packages available in the mirror.
        If `suite` is given, ignore all other suites.

        Side effect: populate the properties suites and packages (beware of the
        interaction between this and passing `suite`: other suites will not be
        considered at all!)

        """
        self._suites = {}
        self._packages = set()

        for cursuite, src_index in self.__find_Sources_gz():
            if suite is not None and cursuite != suite:
                continue
            with open(src_index) as i:
                for pkg in SourcePackage.iter_paragraphs(i):
                    pkg_id = (pkg['package'], pkg['version'])

                    if cursuite not in self._suites:
                        self._suites[cursuite] = []
                    self._suites[cursuite].append(pkg_id)

                    if pkg_id not in self._packages:
                        self._packages.add(pkg_id)
                        pkg['x-debsources-mirror-root'] = self.mirror_root
                        yield pkg

    def ls_suites(self, aliases=False):
        """list suites available in the archive

        if `aliases` is True (default is False) also includes aliased suite
        names, e.g.: "Debian-1.3.1" -> "bo", or "testing" -> "jessie"

        """
        suites = []
        for f in os.listdir(self._dists_dir):
            path = os.path.join(self._dists_dir, f)
            if os.path.islink(path) and not aliases:
                continue
            if os.path.isdir(path):
                suites.append(f)

        return suites

    def ls_suites_with_aliases(self):
        """ list suites, as well as their aliases

        Return value: { suite: [aliases] }
        Example: { sid: [unstable], jessie: [testing] }

        """
        suites = {}

        def add_suite(suite):
            if suite not in suites:
                suites[suite] = []

        for f in os.listdir(self._dists_dir):
            path = os.path.join(self._dists_dir, f)
            if os.path.isdir(path):
                if not os.path.islink(path):
                    add_suite(f)
                else:
                    add_suite(os.readlink(path))
                    suites[os.readlink(path)].append(f)

        return suites


class SourceMirrorArchive(SourceMirror):
    """Handle for a local Debian source mirror archive, i.e. a mirror of
    archive.debian.org content, where different suites might have different
    archive formats

    """

    pass
