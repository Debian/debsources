# Copyright (C) 2013-2014  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
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

import warnings
from pathlib import Path

from sqlalchemy import Column, ForeignKey
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy import Index
from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy import Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.types

from debsources.consts import VCS_TYPES, SLOCCOUNT_LANGUAGES, \
    CTAGS_LANGUAGES, METRIC_TYPES, COPYRIGHT_ORACLES

Base = declarative_base()


# used for migrations, see scripts under debsources/migrate/
DB_SCHEMA_VERSION = 11


class PackageName(Base):
    """ a source package name """
    __tablename__ = 'package_names'

    id = Column(BIGINT, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("Package", backref="name",
                            cascade="all, delete-orphan",
                            passive_deletes=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def to_dict(self):
        """
        simply serializes a package (because SQLAlchemy query results
        aren't serializable
        """
        return dict(name=self.name)


class Package(Base):
    """ a (versioned) source package """
    __tablename__ = 'packages'

    id = Column(BIGINT, primary_key=True)
    version = Column(String, index=True)
    name_id = Column(BIGINT,
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

    id = Column(BIGINT, primary_key=True)
    package_id = Column(BIGINT,
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


class PathType(sqlalchemy.types.TypeDecorator):
    """A custom binary type to work with pathlib.Path.

    When writing in DB: Path -> bytes.
    When reading from DB: bytes -> Path, using surrogateescape for non utf8 bytes.
    """

    impl = sqlalchemy.types.LargeBinary

    def process_bind_param(self, value, dialect):
        if isinstance(value, Path):
            return bytes(value)
        warnings.warn(f"A PathType was not created as a pathlib.Path: {str(value)}")
        return value

    def process_result_value(self, value, dialect):
        # We need a string for pathlib.Path to work. File and folder names are
        # bytes, and are not (necessarily) linked to an encoding, so we do a
        # lossless conversion with surrogateescape.
        value_str = value.decode('utf8', 'surrogateescape')
        return Path(value_str)


class File(Base):
    """source file table"""

    __tablename__ = 'files'
    __table_args__ = (UniqueConstraint('package_id', 'path'),)

    id = Column(BIGINT, primary_key=True)
    package_id = Column(BIGINT,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    path = Column(PathType, index=True,  # path/whitin/source/pkg
                  nullable=False)

    def __init__(self, version, path):
        self.package_id = version.id
        self.path = path


class Checksum(Base):
    __tablename__ = 'checksums'
    __table_args__ = (UniqueConstraint('package_id', 'file_id'),)

    id = Column(BIGINT, primary_key=True)
    package_id = Column(BIGINT,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    file_id = Column(BIGINT,
                     ForeignKey('files.id', ondelete="CASCADE"),
                     index=True, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)

    def __init__(self, version, file_id, sha256):
        self.package_id = version.id
        self.file_id = file_id
        self.sha256 = sha256


class BinaryName(Base):
    __tablename__ = 'binary_names'

    id = Column(BIGINT, primary_key=True)
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

    id = Column(BIGINT, primary_key=True)
    version = Column(String)
    name_id = Column(BIGINT,
                     ForeignKey('binary_names.id', ondelete="CASCADE"),
                     index=True, nullable=False)
    package_id = Column(BIGINT,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)

    def __init__(self, version, area="main"):
        self.version = version

    def __repr__(self):
        return self.version


class SlocCount(Base):
    __tablename__ = 'sloccounts'
    __table_args__ = (UniqueConstraint('package_id', 'language'),)

    id = Column(BIGINT, primary_key=True)
    package_id = Column(BIGINT,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    language = Column(Enum(*SLOCCOUNT_LANGUAGES, name="language_names"),
                      # TODO rename enum s/language_names/sloccount/languages
                      nullable=False)
    count = Column(BIGINT, nullable=False)

    def __init__(self, version, lang, locs):
        self.package_id = version.id
        self.language = lang
        self.count = locs


class Ctag(Base):
    __tablename__ = 'ctags'

    id = Column(BIGINT, primary_key=True)
    package_id = Column(BIGINT,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    tag = Column(String, nullable=False, index=True)
    file_id = Column(BIGINT,
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


class Metric(Base):
    __tablename__ = 'metrics'
    __table_args__ = (UniqueConstraint('package_id', 'metric'),)

    id = Column(BIGINT, primary_key=True)
    package_id = Column(BIGINT,
                        ForeignKey('packages.id', ondelete="CASCADE"),
                        index=True, nullable=False)
    metric = Column(Enum(*METRIC_TYPES, name="metric_types"), nullable=False)
    value = Column("value_", BIGINT, nullable=False)

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

    disk_usage = Column(BIGINT, nullable=True)
    source_files = Column(BIGINT, nullable=True)

    ctags = Column(BIGINT, nullable=True)

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
    lang_ada = Column(BIGINT, nullable=True)
    lang_ansic = Column(BIGINT, nullable=True)
    lang_asm = Column(BIGINT, nullable=True)
    lang_awk = Column(BIGINT, nullable=True)
    lang_cobol = Column(BIGINT, nullable=True)
    lang_cpp = Column(BIGINT, nullable=True)
    lang_cs = Column(BIGINT, nullable=True)
    lang_csh = Column(BIGINT, nullable=True)
    lang_erlang = Column(BIGINT, nullable=True)
    lang_exp = Column(BIGINT, nullable=True)
    lang_f90 = Column(BIGINT, nullable=True)
    lang_fortran = Column(BIGINT, nullable=True)
    lang_haskell = Column(BIGINT, nullable=True)
    lang_java = Column(BIGINT, nullable=True)
    lang_javascript = Column(BIGINT, nullable=True)
    lang_jsp = Column(BIGINT, nullable=True)
    lang_lex = Column(BIGINT, nullable=True)
    lang_lisp = Column(BIGINT, nullable=True)
    lang_makefile = Column(BIGINT, nullable=True)
    lang_ml = Column(BIGINT, nullable=True)
    lang_modula3 = Column(BIGINT, nullable=True)
    lang_objc = Column(BIGINT, nullable=True)
    lang_pascal = Column(BIGINT, nullable=True)
    lang_perl = Column(BIGINT, nullable=True)
    lang_php = Column(BIGINT, nullable=True)
    lang_python = Column(BIGINT, nullable=True)
    lang_ruby = Column(BIGINT, nullable=True)
    lang_sed = Column(BIGINT, nullable=True)
    lang_sh = Column(BIGINT, nullable=True)
    lang_sql = Column(BIGINT, nullable=True)
    lang_tcl = Column(BIGINT, nullable=True)
    lang_vhdl = Column(BIGINT, nullable=True)
    lang_xml = Column(BIGINT, nullable=True)
    lang_yacc = Column(BIGINT, nullable=True)

    def __init__(self, suite, timestamp):
        self.suite = suite
        self.timestamp = timestamp


class FileCopyright(Base):

    __tablename__ = 'copyright'

    id = Column(BIGINT, primary_key=True)
    file_id = Column(BIGINT,
                     ForeignKey('files.id', ondelete="CASCADE"),
                     index=True, nullable=False)
    oracle = Column(Enum(*COPYRIGHT_ORACLES, name="copyright_oracles"),
                    nullable=False)
    license = Column(String)

    def __init__(self, file_id, oracle, license):
        self.file_id = file_id
        self.oracle = oracle
        self.license = license

    def to_dict(self):
        """ Serialize the object
        """
        return dict(file_id=self.file_id,
                    oracle=self.oracle,
                    license=self.license)


class HistoryCopyright(Base):

    __tablename__ = 'history_copyright'

    id = Column(BIGINT, primary_key=True)
    timestamp = Column(DateTime(timezone=False),
                       index=True, nullable=False)
    suite = Column(String,      # suite == "ALL" means totals
                   index=True, nullable=False)
    license = Column(String)
    files = Column(BIGINT, nullable=True)

    def __init__(self, suite, timestamp):
        self.suite = suite
        self.timestamp = timestamp
