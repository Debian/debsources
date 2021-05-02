# Copyright (C) 2013-2015  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
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

import magic
import fnmatch
from pathlib import Path

from sqlalchemy import and_

from debsources.models import Checksum, File, Package, PackageName
from debsources import filetype
from debsources.url import url_encode
from debsources.consts import AREAS
from debsources.debmirror import SourcePackage
from debsources.excepts import FileOrFolderNotFound, InvalidPackageOrVersionError
import debsources.query as qry


class Location(object):
    """a location in a package, can be a directory or a file"""

    def _get_debian_path(self, session, package, version, sources_dir) -> Path:
        """
        Returns the Debian path of a package version.
        For example: main/h
                     contrib/libz
        It's the path of a *version*, since a package can have multiple
        versions in multiple areas (ie main/contrib/nonfree).

        sources_dir: the sources directory, usually comes from the app config
        """
        prefix = SourcePackage.pkg_prefix(package)

        try:
            p_id = (
                session.query(PackageName)
                .filter(PackageName.name == package)
                .first()
                .id
            )
            varea = (
                session.query(Package)
                .filter(and_(Package.name_id == p_id, Package.version == version))
                .first()
                .area
            )
        except:
            # the package or version doesn't exist in the database
            # BUT: packages are stored for a longer time in the filesystem
            # to allow codesearch.d.n and others less up-to-date platforms
            # to point here.
            # Problem: we don't know the area of such a package
            # so we try in main, contrib and non-free.
            for area in AREAS:
                if Path.exists(Path(sources_dir) / area / prefix / package / version):
                    return Path(area) / prefix

            raise InvalidPackageOrVersionError("%s %s" % (package, version))

        return Path(varea) / prefix

    def __init__(
        self, session, sources_dir, sources_static, package, version="", path=""
    ):
        """initialises useful attributes"""
        debian_path = self._get_debian_path(session, package, version, sources_dir)
        self.package = package
        self.version = version
        self.path = Path(path)
        self.path_to = Path(package) / version / path

        self.sources_path = Path(sources_dir) / debian_path / self.path_to

        self.version_path = Path(sources_dir) / debian_path / package / version

        if not Path.exists(self.sources_path):
            raise FileOrFolderNotFound("%s" % (self.path_to))

        self.sources_path_static = Path(sources_static) / debian_path / self.path_to

    def is_dir(self):
        """True if self is a directory, False if it's not"""
        return self.sources_path.is_dir()

    def is_file(self):
        """True if sels is a file, False if it's not"""
        return self.sources_path.is_file()

    def is_symlink(self):
        """True if a folder/file is a symbolic link file, False if it's not"""
        return self.sources_path.is_symlink()

    def get_package(self):
        return self.package

    def get_version(self):
        return self.version

    def get_path(self):
        return self.path

    def get_deepest_element(self):
        if self.version == "":
            return self.package
        elif self.path == Path():  # empty path
            return self.version
        else:
            return self.path.name

    def get_path_to(self):
        return self.path_to


class Directory(object):
    """a folder in a package"""

    def __init__(self, location, hidden_files=[]):
        # if the directory is a toplevel one, we remove the .pc folder
        self.sources_path = location.sources_path
        self.location = location
        self.hidden_files = hidden_files

    def get_listing(self):
        """
        returns the list of folders/files in a directory,
        along with their type (directory/file)
        in a tuple (name, type)
        """

        def get_type(f):
            if Path.is_dir(self.sources_path / f):
                return "directory"
            else:
                return "file"

        listing = [
            {
                "name": url_encode(f.name),
                "type": get_type(f),
                "hidden": False,
                "stat": qry.location_get_stat(self.sources_path / f),
            }
            for f in sorted(Path.iterdir(self.sources_path))
        ]

        for hidden_file in self.hidden_files:
            for f in listing:
                full_path = bytes(self.location.sources_path / f["name"])
                if f["type"] == "directory":
                    full_path += b"/"
                f["hidden"] = f["hidden"] or fnmatch.fnmatch(full_path, hidden_file)

        return listing


class SourceFile(object):
    """a source file in a package"""

    def __init__(self, location):
        self.location = location
        self.sources_path = location.sources_path
        self.sources_path_static = location.sources_path_static
        self.mime = self._find_mime()

    def _find_mime(self):
        """returns the mime encoding and type of a file"""
        mime = magic.open(magic.MIME_TYPE)
        mime.load()
        type_ = mime.file(self.sources_path)
        mime.close()
        mime = magic.open(magic.MIME_ENCODING)
        mime.load()
        encoding = mime.file(self.sources_path)
        mime.close()
        return dict(encoding=encoding, type=type_)

    def get_mime(self):
        return self.mime

    def get_sha256sum(self, session):
        """
        Queries the DB and returns the shasum of the file.
        """
        shasum = (
            session.query(Checksum.sha256)
            .filter(Checksum.package_id == Package.id)
            .filter(Package.name_id == PackageName.id)
            .filter(File.id == Checksum.file_id)
            .filter(PackageName.name == self.location.package)
            .filter(Package.version == self.location.version)
            .filter(File.path == self.location.path)
            .first()
        )
        # WARNING: in the DB path is binary, and here
        # location.path is unicode, because the path comes from
        # the URL. TODO: check with non-unicode paths
        if shasum:
            shasum = shasum[0]
        return shasum

    def istextfile(self):
        """True if self is a text file, False if it's not."""
        return filetype.is_text_file(self.mime["type"])
        # for substring in text_file_mimes:
        #     if substring in self.mime['type']:
        #         return True
        # return False

    def get_raw_url(self):
        """return the raw url on disk (e.g. data/main/a/azerty/foo.bar)"""
        return url_encode(str(self.sources_path_static))
