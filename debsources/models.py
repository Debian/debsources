# Copyright (C) 2013-2014  Matthieu Caneill <matthieu.caneill@gmail.com>
#                          Stefano Zacchiroli <zack@upsilon.cc>
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

import os
import magic
import stat
import fnmatch
from collections import namedtuple

from sqlalchemy import Column, ForeignKey
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy import Index
from sqlalchemy import Boolean, Date, DateTime, Integer, LargeBinary, String
from sqlalchemy import Enum
from sqlalchemy import and_
from sqlalchemy import func as sql_func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from debian.debian_support import version_compare

from debsources.excepts import InvalidPackageOrVersionError, \
    FileOrFolderNotFound
from debsources.consts import VCS_TYPES, SLOCCOUNT_LANGUAGES, \
    CTAGS_LANGUAGES, METRIC_TYPES, AREAS, PREFIXES_DEFAULT
from debsources import filetype
from debsources.debmirror import SourcePackage
from debsources.consts import SUITES

Base = declarative_base()


# used for migrations, see scripts under debsources/migrate/
DB_SCHEMA_VERSION = 8


class PackageName(Base):
    """ a source package name """
    __tablename__ = 'package_names'

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("Package", backref="name",
                            cascade="all, delete-orphan",
                            passive_deletes=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    @staticmethod
    def get_packages_prefixes(cache_dir):
        """
        returns the packages prefixes (a, b, ..., liba, libb, ..., y, z)
        cache_dir: the cache directory, usually comes from the app config
        """
        try:
            with open(os.path.join(cache_dir, 'pkg-prefixes')) as f:
                prefixes = [l.rstrip() for l in f]
        except IOError:
            prefixes = PREFIXES_DEFAULT
        return prefixes

    @staticmethod
    def list_versions(session, packagename, suite=""):
        """
        return all versions of a packagename. if suite is specified, only
        versions contained in that suite are returned.
        """
        try:
            name_id = session.query(PackageName) \
                             .filter(PackageName.name == packagename) \
                             .first().id
        except Exception:
            raise InvalidPackageOrVersionError(packagename)
        try:
            if not suite:
                versions = session.query(Package) \
                                  .filter(Package.name_id == name_id).all()
            else:
                versions = (session.query(Package)
                                   .filter(Package.name_id == name_id)
                                   .filter(sql_func.lower(Suite.suite)
                                           == suite)
                                   .filter(Suite.package_id == Package.id)
                                   .all())
        except Exception:
            raise InvalidPackageOrVersionError(packagename)
        # we sort the versions according to debian versions rules
        versions = sorted(versions, cmp=version_compare)
        return versions

    @staticmethod
    def list_versions_w_suites(session, packagename, suite=""):
        """
        return versions with suites. if suite is provided, then only return
        versions contained in that suite.
        """
        # FIXME a left outer join on (Package, Suite) is more preferred.
        # However, per https://stackoverflow.com/a/997467, custom aggregation
        # function to concatenate the suite names for the group_by should be
        # defined on database connection level.
        versions = PackageName.list_versions(session, packagename, suite)
        versions_w_suites = []
        try:
            for v in versions:
                suites = session.query(Suite) \
                                .filter(Suite.package_id == v.id) \
                                .all()
                # sort the suites according to debsources.consts.SUITES
                # use keyfunc to make it py3 compatible
                suites.sort(key=lambda s: SUITES['all'].index(s.suite))
                suites = [s.suite for s in suites]
                v = v.to_dict()
                v['suites'] = suites
                versions_w_suites.append(v)
        except Exception:
            raise InvalidPackageOrVersionError(packagename)

        return versions_w_suites

    def to_dict(self):
        """
        simply serializes a package (because SQLAlchemy query results
        aren't serializable
        """
        return dict(name=self.name)


class Package(Base):
    """ a (versioned) source package """
    __tablename__ = 'packages'

    id = Column(Integer, primary_key=True)
    version = Column(String, index=True)
    name_id = Column(Integer,
                     ForeignKey('package_names.id', ondelete="CASCADE"),
                     index=True, nullable=False)
    area = Column(String(8), index=True)  # main, contrib, non-free
    vcs_type = Column(Enum(*VCS_TYPES, name="vcs_types"))
    vcs_url = Column(String)
    vcs_browser = Column(String)

    # whether this package should survive GC no matter what
    sticky = Column(Boolean, nullable=False)

    def __init__(self, version, package, sticky=False):
        self.version = version
        self.name_id = package.id
        self.sticky = sticky

    def __repr__(self):
        return self.version

    def to_dict(self):
        """
        simply serializes a version (because SQLAlchemy query results
        aren't serializable
        """
        return dict(version=self.version, area=self.area)

Index('ix_packages_name_id_version', Package.name_id, Package.version)


class Suite(Base):
    """
    Debian suites (squeeze, wheezy, etc) mapping with source package versions
    """
    __tablename__ = 'suites'
    __table_args__ = (UniqueConstraint('package_id', 'suite'),)

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    suite = Column(String, index=True)

    def __init__(self, package, suite):
        self.package_id = package.id
        self.suite = suite


class SuiteInfo(Base):
    """static information about known suites

    Note: currently used only for sticky suites.
    """
    # TODO cross-reference Suite to this table

    __tablename__ = 'suites_info'

    name = Column(String, primary_key=True)
    version = Column(String, nullable=True)
    release_date = Column(Date, nullable=True)
    sticky = Column(Boolean, nullable=False)
    aliases = relationship("SuiteAlias")

    def __init__(self, name, sticky=False, version=None, release_date=None,
                 aliases=[]):
        self.name = name
        if version:
            self.version = version
        if release_date:
            self.release_date = release_date
        self.sticky = sticky
        if aliases:
            self.aliases = aliases


class SuiteAlias(Base):
    """ Aliases for suites (ie: unstable for sid) """

    __tablename__ = "suites_aliases"
    alias = Column(String, primary_key=True)
    suite = Column(String, ForeignKey('suites_info.name', ondelete='CASCADE'))


class File(Base):
    """source file table"""

    __tablename__ = 'files'
    __table_args__ = (UniqueConstraint('package_id', 'path'),)

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    path = Column(LargeBinary, index=True,  # path/whitin/source/pkg
                  nullable=False)

    def __init__(self, version, path):
        self.package_id = version.id
        self.path = path


class Checksum(Base):
    __tablename__ = 'checksums'
    __table_args__ = (UniqueConstraint('package_id', 'file_id'),)

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    file_id = Column(Integer,
                     ForeignKey('files.id', ondelete="CASCADE"),
                     index=True, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)

    def __init__(self, version, file_id, sha256):
        self.package_id = version.id
        self.file_id = file_id
        self.sha256 = sha256


class BinaryName(Base):
    __tablename__ = 'binary_names'

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("Binary", backref="name",
                            cascade="all, delete-orphan",
                            passive_deletes=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class Binary(Base):
    __tablename__ = 'binaries'

    id = Column(Integer, primary_key=True)
    version = Column(String)
    name_id = Column(Integer,
                     ForeignKey('binary_names.id', ondelete="CASCADE"),
                     index=True, nullable=False)
    package_id = Column(Integer,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)

    def __init__(self, version, area="main"):
        self.version = version

    def __repr__(self):
        return self.version


class SlocCount(Base):
    __tablename__ = 'sloccounts'
    __table_args__ = (UniqueConstraint('package_id', 'language'),)

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    language = Column(Enum(*SLOCCOUNT_LANGUAGES, name="language_names"),
                      # TODO rename enum s/language_names/sloccount/languages
                      nullable=False)
    count = Column(Integer, nullable=False)

    def __init__(self, version, lang, locs):
        self.package_id = version.id
        self.language = lang
        self.count = locs


class Ctag(Base):
    __tablename__ = 'ctags'

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    tag = Column(String, nullable=False, index=True)
    file_id = Column(Integer,
                     ForeignKey('files.id', ondelete="CASCADE"),
                     index=True, nullable=False)
    line = Column(Integer, nullable=False)
    kind = Column(String)  # see `ctags --list-kinds`; unfortunately ctags
    # gives no guarantee of uniformity in kinds, they might be one-lettered
    # or full names, sigh
    language = Column(Enum(*CTAGS_LANGUAGES, name="ctags_languages"))

    def __init__(self, version, tag, file_id, line, kind, language):
        self.package_id = version.id
        self.tag = tag
        self.file_id = file_id
        self.line = line
        self.kind = kind
        self.language = language

    # TODO:
    # after refactoring, when we'll have a File table the query to get a list
    # of files containing a list of tags will be simpler
    #
    # def find_files_containing(self, session, ctags, package=None):
    #     """
    #     Returns a list of files containing all the ctags.
    #
    #     session: SQLAlchemy session
    #     ctags: [tags]
    #     package: limit search in package
    #     """
    #     results = (session.query(Ctag.path, Ctag.package_id)
    #                .filter(Ctag.tag in ctags)
    #                .filter(Ctag

    @staticmethod
    def find_ctag(session, ctag, package=None, slice_=None):
        """
        Returns places in the code where a ctag is found.
             tuple (count, [sliced] results)

        session: an SQLAlchemy session
        ctag: the ctag to search
        package: limit results to package
        """

        results = (session.query(PackageName.name.label("package"),
                                 Package.version.label("version"),
                                 Ctag.file_id.label("file_id"),
                                 File.path.label("path"),
                                 Ctag.line.label("line"))
                   .filter(Ctag.tag == ctag)
                   .filter(Ctag.package_id == Package.id)
                   .filter(Ctag.file_id == File.id)
                   .filter(Package.name_id == PackageName.id)
                   )
        if package is not None:
            results = results.filter(PackageName.name == package)

        results = results.order_by(Ctag.package_id, File.path)
        count = results.count()
        if slice_ is not None:
            results = results.slice(slice_[0], slice_[1])
        results = [dict(package=res.package,
                        version=res.version,
                        path=res.path,
                        line=res.line)
                   for res in results.all()]
        return (count, results)


class Metric(Base):
    __tablename__ = 'metrics'
    __table_args__ = (UniqueConstraint('package_id', 'metric'),)

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    metric = Column(Enum(*METRIC_TYPES, name="metric_types"), nullable=False)
    value = Column("value_", Integer, nullable=False)

    def __init__(self, version, metric, value):
        self.package_id = version.id
        self.metric = metric
        self.value = value


class HistorySize(Base):
    """historical record of debsources size"""

    __tablename__ = 'history_size'
    __table_args__ = (PrimaryKeyConstraint('timestamp', 'suite'),)

    timestamp = Column(DateTime(timezone=False),
                       index=True, nullable=False)
    suite = Column(String,		# suite == "ALL" means totals
                   index=True, nullable=False)

    source_packages = Column(Integer, nullable=True)
    binary_packages = Column(Integer, nullable=True)

    disk_usage = Column(Integer, nullable=True)
    source_files = Column(Integer, nullable=True)

    ctags = Column(Integer, nullable=True)

    def __init__(self, suite, timestamp):
        self.suite = suite
        self.timestamp = timestamp


class HistorySlocCount(Base):
    """historical record of debsources languages"""

    __tablename__ = 'history_sloccount'
    __table_args__ = (PrimaryKeyConstraint('timestamp', 'suite'),)

    timestamp = Column(DateTime(timezone=False),
                       index=True, nullable=False)
    suite = Column(String,		# suite == "ALL" means totals
                   index=True, nullable=False)

    # see consts.SLOCCOUNT_LANGUAGES for the language list rationale
    lang_ada = Column(Integer, nullable=True)
    lang_ansic = Column(Integer, nullable=True)
    lang_asm = Column(Integer, nullable=True)
    lang_awk = Column(Integer, nullable=True)
    lang_cobol = Column(Integer, nullable=True)
    lang_cpp = Column(Integer, nullable=True)
    lang_cs = Column(Integer, nullable=True)
    lang_csh = Column(Integer, nullable=True)
    lang_erlang = Column(Integer, nullable=True)
    lang_exp = Column(Integer, nullable=True)
    lang_f90 = Column(Integer, nullable=True)
    lang_fortran = Column(Integer, nullable=True)
    lang_haskell = Column(Integer, nullable=True)
    lang_java = Column(Integer, nullable=True)
    lang_jsp = Column(Integer, nullable=True)
    lang_lex = Column(Integer, nullable=True)
    lang_lisp = Column(Integer, nullable=True)
    lang_makefile = Column(Integer, nullable=True)
    lang_ml = Column(Integer, nullable=True)
    lang_modula3 = Column(Integer, nullable=True)
    lang_objc = Column(Integer, nullable=True)
    lang_pascal = Column(Integer, nullable=True)
    lang_perl = Column(Integer, nullable=True)
    lang_php = Column(Integer, nullable=True)
    lang_python = Column(Integer, nullable=True)
    lang_ruby = Column(Integer, nullable=True)
    lang_sed = Column(Integer, nullable=True)
    lang_sh = Column(Integer, nullable=True)
    lang_sql = Column(Integer, nullable=True)
    lang_tcl = Column(Integer, nullable=True)
    lang_vhdl = Column(Integer, nullable=True)
    lang_xml = Column(Integer, nullable=True)
    lang_yacc = Column(Integer, nullable=True)

    def __init__(self, suite, timestamp):
        self.suite = suite
        self.timestamp = timestamp

# it's used in Location.get_stat
# to bypass flake8 complaints, we do not inject the global namespace
# with globals()["LongFMT"] = namedtuple...
LongFMT = namedtuple("LongFMT", ["type", "perms", "size", "symlink_dest"])


class Location(object):
    """ a location in a package, can be a directory or a file """

    def _get_debian_path(self, session, package, version, sources_dir):
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
            p_id = session.query(PackageName) \
                          .filter(PackageName.name == package).first().id
            varea = session.query(Package) \
                           .filter(and_(Package.name_id == p_id,
                                        Package.version == version)) \
                           .first().area
        except:
            # the package or version doesn't exist in the database
            # BUT: packages are stored for a longer time in the filesystem
            # to allow codesearch.d.n and others less up-to-date platforms
            # to point here.
            # Problem: we don't know the area of such a package
            # so we try in main, contrib and non-free.
            for area in AREAS:
                if os.path.exists(os.path.join(sources_dir, area,
                                               prefix, package, version)):
                    return os.path.join(area, prefix)

            raise InvalidPackageOrVersionError("%s %s" % (package, version))

        return os.path.join(varea, prefix)

    def __init__(self, session, sources_dir, sources_static,
                 package, version="", path=""):
        """ initialises useful attributes """
        debian_path = self._get_debian_path(session,
                                            package, version, sources_dir)
        self.package = package
        self.version = version
        self.path = path
        self.path_to = os.path.join(package, version, path)

        self.sources_path = os.path.join(
            sources_dir,
            debian_path,
            self.path_to)

        self.version_path = os.path.join(
            sources_dir,
            debian_path,
            package,
            version)

        if not(os.path.exists(self.sources_path)):
            raise FileOrFolderNotFound("%s" % (self.path_to))

        self.sources_path_static = os.path.join(
            sources_static,
            debian_path,
            self.path_to)

    def is_dir(self):
        """ True if self is a directory, False if it's not """
        return os.path.isdir(self.sources_path)

    def is_file(self):
        """ True if sels is a file, False if it's not """
        return os.path.isfile(self.sources_path)

    def is_symlink(self):
        """ True if a folder/file is a symbolic link file, False if it's not
        """
        return os.path.islink(self.sources_path)

    def get_package(self):
        return self.package

    def get_version(self):
        return self.version

    def get_path(self):
        return self.path

    def get_deepest_element(self):
        if self.version == "":
            return self.package
        elif self.path == "":
            return self.version
        else:
            return self.path.split("/")[-1]

    def get_path_to(self):
        return self.path_to.rstrip("/")

    @staticmethod
    def get_stat(sources_path):
        """
        Returns the filetype and permissions of the folder/file
        on the disk, unix-styled.
        """
        # When porting to Python3, use stat.filemode directly
        sources_stat = os.lstat(sources_path)
        sources_mode, sources_size = sources_stat.st_mode, sources_stat.st_size
        perm_flags = [
            (stat.S_IRUSR, "r", "-"),
            (stat.S_IWUSR, "w", "-"),
            (stat.S_IXUSR, "x", "-"),
            (stat.S_IRGRP, "r", "-"),
            (stat.S_IWGRP, "w", "-"),
            (stat.S_IXGRP, "x", "-"),
            (stat.S_IROTH, "r", "-"),
            (stat.S_IWOTH, "w", "-"),
            (stat.S_IXOTH, "x", "-"),
            ]
        # XXX these flags should be enough.
        type_flags = [
            (stat.S_ISLNK, "l"),
            (stat.S_ISREG, "-"),
            (stat.S_ISDIR, "d"),
            ]
        # add the file type: d/l/-
        file_type = " "
        for ft, sign in type_flags:
            if ft(sources_mode):
                file_type = sign
                break
        file_perms = ""
        for (flag, do_true, do_false) in perm_flags:
            file_perms += do_true if (sources_mode & flag) else do_false

        file_size = sources_size

        symlink_dest = None
        if file_type == "l":
            symlink_dest = os.readlink(sources_path)

        return vars(LongFMT(file_type, file_perms, file_size, symlink_dest))

    @staticmethod
    def get_path_links(endpoint, path_to):
        """
        returns the path hierarchy with urls, to use with 'You are here:'
        [(name, url(name)), (...), ...]
        """
        path_dict = path_to.split('/')
        pathl = []

        # we import flask here, in order to permit the use of this module
        # without requiring the user to have flask (e.g. bin/debsources-update
        # can run in another machine without flask, because it doesn't use
        # this method)
        from flask import url_for

        for (i, p) in enumerate(path_dict):
            pathl.append((p, url_for(endpoint,
                                     path_to='/'.join(path_dict[:i+1]))))
        return pathl


class Directory(object):
    """ a folder in a package """

    def __init__(self, location, hidden_files=[]):
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
            if os.path.isdir(os.path.join(self.sources_path, f)):
                return "directory"
            else:
                return "file"
        get_stat, join_path = self.location.get_stat, os.path.join
        listing = sorted(dict(name=f, type=get_type(f), hidden=False,
                              stat=get_stat(join_path(self.sources_path, f)))
                         for f in os.listdir(self.sources_path))

        for hidden_file in self.hidden_files:
            for f in listing:
                full_path = os.path.join(self.location.sources_path, f['name'])
                if f['type'] == "directory":
                    full_path += "/"
                f['hidden'] = (f['hidden']
                               or fnmatch.fnmatch(full_path, hidden_file))

        return listing


class SourceFile(object):
    """ a source file in a package """

    def __init__(self, location):
        self.location = location
        self.sources_path = location.sources_path
        self.sources_path_static = location.sources_path_static
        self.mime = self._find_mime()

    def _find_mime(self):
        """ returns the mime encoding and type of a file """
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
        shasum = session.query(Checksum.sha256) \
                        .filter(Checksum.package_id == Package.id) \
                        .filter(Package.name_id == PackageName.id) \
                        .filter(File.id == Checksum.file_id) \
                        .filter(PackageName.name == self.location.package) \
                        .filter(Package.version == self.location.version) \
                        .filter(File.path == str(self.location.path)) \
                        .first()
        # WARNING: in the DB path is binary, and here
        # location.path is unicode, because the path comes from
        # the URL. TODO: check with non-unicode paths
        if shasum:
            shasum = shasum[0]
        return shasum

    def istextfile(self):
        """True if self is a text file, False if it's not.

        """
        return filetype.is_text_file(self.mime['type'])
        # for substring in text_file_mimes:
        #     if substring in self.mime['type']:
        #         return True
        # return False

    def get_raw_url(self):
        """ return the raw url on disk (e.g. data/main/a/azerty/foo.bar) """
        return self.sources_path_static
