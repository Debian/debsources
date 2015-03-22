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

from sqlalchemy import Column, ForeignKey
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy import Index
from sqlalchemy import Boolean, Date, DateTime, Integer, LargeBinary, String
from sqlalchemy import Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


from debsources.consts import VCS_TYPES, SLOCCOUNT_LANGUAGES, \
    CTAGS_LANGUAGES, METRIC_TYPES

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
