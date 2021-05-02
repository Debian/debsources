# Copyright (C) 2013-2021  The Debsources developers
# <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


import logging
import lzma
import magic
import os
from pathlib import Path
from typing import Optional

from debian import deb822

# supported compression formats for Sources files. Order does matter: formats
# appearing early in the list will be preferred to those appearing later
SOURCES_COMP_FMTS = ["gz", "xz"]


class DebmirrorError(RuntimeError):
    """runtime error when using a local Debian mirror"""

    pass


class SourcePackage(deb822.Sources):
    """Debian source package, as it appears in a source mirror"""

    @classmethod
    def from_db_model(cls, db_package):
        """build a (mock) SourcePackage object from a models.Package instance

        note that the built object will not contain all the needed source
        package information, but only those that can be reconstructed using
        information available in the Debsources db.  That, however, should be
        enough for the purposes of Debsources' needs.

        """
        meta = {}
        meta["package"] = db_package.name.name
        meta["version"] = db_package.version
        meta["section"] = db_package.area
        return cls(meta)

    # override deb822's __eq__, as in source package land we can rely on
    # <package, version> pair uniqueness
    def __eq__(self, other):
        """equality based on <package, version> paris only"""
        if self["package"] != other["package"]:
            return False
        if self["version"] != other["version"]:
            return False
        return True

    # This used to exist in the Python 2 version of Debsources, but doesn't
    # seem to be in use. Outdated stuff is normally deleted, but since the
    # comparison of 2 source packages does imply the logic below, it is
    # exceptionnally kept here commented out in case this actually needs to be
    # implemented with Python 3.

    # def __cmp__(self, other):
    #     """comparison based on <package, version> pairs only
    #     """
    #     cmp1 = cmp(self['package'], other['package'])
    #     if cmp1:  # 'package' key is enough to discriminate
    #         return cmp1
    #     return version_compare(self['version'], other['version'])

    def __hash__(self):
        """compute hash based on <package, version> pair only"""
        return hash((self["package"], self["version"]))

    def __str__(self):
        """package/version representation of a package"""
        return "%s/%s" % (self["package"], self["version"])

    __repr__ = __str__
    __unicode__ = __str__

    def archive_area(self):
        """return package are in the debian achive

        one of: main, contrib, non-free. Return `None` if the archive area
        cannot be figured out

        """
        area = None
        try:
            sec = self["section"]
            if sec.startswith("contrib"):
                area = "contrib"
            elif sec.startswith("non-free"):
                area = "non-free"
            else:
                area = "main"
        except KeyError:  # section not found, might happen in some old
            # buggy packages; try an heuristic
            try:
                directory = self["directory"]
                steps = directory.split("/")
                if "non-free" in steps:
                    area = "non-free"
                elif "contrib" in steps:
                    area = "contrib"
                else:
                    area = "main"
                logging.warn("guessed archive area %s for package %s" % (area, self))
            except KeyError:
                area = None

        return area

    @staticmethod
    def pkg_prefix(pkgname):
        """compute package prefix in the pool structure, for pkgname

        same as prefix(), but static method, used to factorize the prefix
        computation logic throughout Debsources

        """
        if pkgname.startswith("lib"):
            prefix = pkgname[:4]
        else:
            prefix = pkgname[:1]
        return prefix.lower()

    def prefix(self):
        """compute package prefix in the pool structure

        e.g.: 1st character of package name or "lib" + 1st char, depending on
        the package
        """
        return self.pkg_prefix(self["package"])

    def dsc_path(self) -> Path:
        """return (absolute) path to .dsc file for this package"""
        files_field = None
        for field in ["checksums-sha256", "files"]:
            if field in self:
                files_field = field
                break
        if not files_field:
            raise ValueError("cannot list components of source package: %s" % self)

        dsc = next(filter(lambda f: f["name"].endswith(".dsc"), self[files_field]))[
            "name"
        ]

        return Path(self["x-debsources-mirror-root"]) / self["directory"] / dsc

    def extraction_dir(self, basedir: Path) -> Optional[Path]:
        """return package extraction dir, relative to debsources sources_dir

        If given, prepend basedir path to the generated path. Return `None` if
        we can't figure out where to extract the package to

        """
        area = self.archive_area()
        if area is None:
            return None

        return basedir / area / self.prefix() / self["package"] / self["version"]


class SourceMirror(object):
    """Handle for a local Debian source mirror"""

    def __init__(self, path: Path):
        """create a handle to a local source mirror rooted at path"""
        self.mirror_root = path
        self._suites = None  # dict: suite name -> [<package, version>]
        self._packages = None  # set(<package, version>)
        self._dists_dir = path / "dists"

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

    def __find_Sources(self):
        """Find Sources entries contained in the mirror, in various supported
        compression formats

        Return them as <suite, path> pairs. It will be up to client code to
        recognize if they are compressed (e.g., based on file extension) and
        uncompress them if needed

        """

        def choose_comp(base: Path) -> Path:
            """pick the preferred compressed variant of a given Sources file"""
            for fmt in SOURCES_COMP_FMTS:
                sources_file = base.with_suffix(f".{fmt}")
                if sources_file.exists():
                    return sources_file
            raise DebmirrorError(
                "no supported compressed variants of " "Sources file: " + base
            )

        for root, dirs, files in os.walk(self._dists_dir):
            src_bases = set(
                Path(root) / Path(file).stem
                for file in files
                if Path(file).stem == "Sources"
            )
            src_indexes = [choose_comp(b) for b in src_bases]
            for f in src_indexes:
                suite = f.parts[-4]  # wheezy, jessie, sid, ...
                yield suite, f

    def pkg_prefixes(self):
        """Return the list of relevant package prefixes

        takes into account Debian convention, e.g. most packages prefix to
        their first letter, except libraries that prefix to libX

        """
        pool_dir: Path = self.mirror_root / "pool"
        prefixes = set()
        for pool_subdir in os.listdir(pool_dir):
            # make it absolute
            pool_subdir: Path = pool_dir / pool_subdir
            for entry in os.listdir(pool_subdir):
                if (pool_subdir / entry).is_dir():
                    prefixes.add(entry)
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

        for cursuite, src_index in self.__find_Sources():
            logging.info("Dealing sources file {}".format(src_index))
            if suite is not None and cursuite != suite:
                continue

            # we check the type of the Sources file
            mime = magic.open(magic.MIME_TYPE + magic.SYMLINK)
            mime.load()
            type_ = mime.file(src_index)
            mime.close()

            with open(src_index) as i:
                if type_ == "application/x-xz":
                    # we need to decompress ourselves xz files
                    content = lzma.decompress(i.read()).decode("utf-8")
                else:
                    content = i

                for pkg in SourcePackage.iter_paragraphs(content):
                    pkg_id = (pkg["package"], pkg["version"])

                    if cursuite not in self._suites:
                        self._suites[cursuite] = []
                    self._suites[cursuite].append(pkg_id)

                    if pkg_id not in self._packages:
                        self._packages.add(pkg_id)
                        pkg["x-debsources-mirror-root"] = str(self.mirror_root)
                        yield pkg

    def ls_suites(self, aliases=False):
        """list suites available in the archive

        if `aliases` is True (default is False) also includes aliased suite
        names, e.g.: "Debian-1.3.1" -> "bo", or "testing" -> "jessie"

        """
        suites = []
        for f in os.listdir(self._dists_dir):
            path: Path = self._dists_dir / f
            if path.is_symlink() and not aliases:
                continue
            if path.is_dir():
                suites.append(f)

        return suites

    def ls_suites_with_aliases(self):
        """list suites, as well as their aliases

        Return value: { suite: [aliases] }
        Example: { sid: [unstable], jessie: [testing] }

        """
        suites = {}

        def add_suite(suite):
            if suite not in suites:
                suites[suite] = []

        for f in os.listdir(self._dists_dir):
            path = self._dists_dir / f
            if path.is_dir():
                if not path.is_symlink():
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
