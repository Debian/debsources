# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#                     Stefano Zacchiroli <zack@upsilon.cc>
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


from sqlalchemy import func as sql_func
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy import Integer, String, Index, Enum, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


# this list should be kept in sync with
# http://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-VCS-fields
VCS_TYPES = ("arch", "bzr", "cvs", "darcs", "git", "hg", "mtn", "svn")

# this list should be kept in sync with languages supported by sloccount. A
# good start is http://www.dwheeler.com/sloccount/sloccount.html (section
# "Basic concepts"). Others have been added to the Debian package via patches.
SLOCCOUNT_LANGUAGES = (

    # sloccount 2.26 languages
    "ada", "asm", "awk", "sh", "ansic", "cpp", "cs", "csh", "cobol", "exp",
    "fortran", "f90", "haskell", "java", "lex", "lisp", "makefile", "ml",
    "modula3", "objc", "pascal", "perl", "php", "python",
    "ruby", "sed", "sql", "tcl", "yacc",

    # enhancements from Debian patches, version 2.26-5
    "erlang", "jsp", "vhdl", "xml",
)

# this list should be kept in sync with languages supported by (exuberant)
# ctags. See: http://ctags.sourceforge.net/languages.html and the output of
# `ctags --list-languages`
CTAGS_LANGUAGES = (
    'ant', 'asm', 'asp', 'awk', 'basic', 'beta', 'c', 'c++',
    'c#', 'cobol', 'dosbatch', 'eiffel', 'erlang', 'flex', 'fortran', 'go',
    'html', 'java', 'javascript', 'lisp', 'lua', 'make', 'matlab',
    'objectivec', 'ocaml', 'pascal', 'perl', 'php', 'python', 'rexx', 'ruby',
    'scheme', 'sh', 'slang', 'sml', 'sql', 'tcl', 'tex', 'vera', 'verilog',
    'vhdl', 'vim', 'yacc',
)

# TODO uniform CTAGS_* language naming (possibly without blessing any of the
# two, but using a 3rd, Debsources specific, canonical form)

METRIC_TYPES = ("size",)


Base = declarative_base()


class Package(Base):
    """ a source package """
    __tablename__ = 'packages'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("Version", backref="package",
                            cascade="all, delete-orphan",
                            passive_deletes=True)
    
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return self.name


class Version(Base):
    """ a version of a source package """
    __tablename__ = 'versions'
    
    id = Column(Integer, primary_key=True)
    vnumber = Column(String)
    package_id = Column(Integer, ForeignKey('packages.id', ondelete="CASCADE"),
                        nullable=False)
    area = Column(String(8), index=True)	# main, contrib, non-free
    vcs_type = Column(Enum(*VCS_TYPES, name="vcs_types"))
    vcs_url = Column(String)
    vcs_browser = Column(String)
    
    def __init__(self, version, package):
        self.vnumber = version
        self.package_id = package.id

    def __repr__(self):
        return self.vnumber

Index('ix_versions_package_id_vnumber', Version.package_id, Version.vnumber)


class SuitesMapping(Base):
    """
    Debian suites (squeeze, wheezy, etc) mapping with source package versions
    """
    __tablename__ = 'suitesmapping'
    
    id = Column(Integer, primary_key=True)
    sourceversion_id = Column(Integer,
                              ForeignKey('versions.id', ondelete="CASCADE"),
                              nullable=False)
    suite = Column(String, index=True)
    

class Checksum(Base):
    __tablename__ = 'checksums'
    __table_args__ = (UniqueConstraint('version_id', 'path'),)

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey('versions.id', ondelete="CASCADE"),
                        nullable=False)
    path = Column(LargeBinary, nullable=False)	# path/whitin/source/pkg
    sha256 = Column(String(64), nullable=False, index=True)

    def __init__(self, version, path, sha256):
        self.version_id = version.id
        self.path = path
        self.sha256 = sha256


class BinaryPackage(Base):
    __tablename__ = 'binarypackages'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("BinaryVersion", backref="binarypackage",
                            cascade="all, delete-orphan",
                            passive_deletes=True)
    
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return self.name


class BinaryVersion(Base):
    __tablename__ = 'binaryversions'
    
    id = Column(Integer, primary_key=True)
    vnumber = Column(String)
    binarypackage_id = Column(Integer, ForeignKey('binarypackages.id',
                                                  ondelete="CASCADE"),
                              nullable=False)
    sourceversion_id = Column(Integer, ForeignKey('versions.id',
                                                  ondelete="CASCADE"),
                              nullable=False)
    
    def __init__(self, vnumber, area="main"):
        self.vnumber = vnumber

    def __repr__(self):
        return self.vnumber


class SlocCount(Base):
    __tablename__ = 'sloccounts'
    __table_args__ = (UniqueConstraint('sourceversion_id', 'language'),)
    
    id = Column(Integer, primary_key=True)
    sourceversion_id = Column(Integer,
                              ForeignKey('versions.id', ondelete="CASCADE"),
                              nullable=False)
    language = Column(Enum(*SLOCCOUNT_LANGUAGES, name="language_names"),
                      # TODO rename enum s/language_names/sloccount/languages
                      nullable=False)
    count = Column(Integer, nullable=False)

    def __init__(self, version, lang, locs):
        self.sourceversion_id = version.id
        self.language = lang
        self.count = locs


class Ctag(Base):
    __tablename__ = 'ctags'

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey('versions.id', ondelete="CASCADE"),
                        nullable=False, index=True)
    tag = Column(String, nullable=False)
    path = Column(LargeBinary, nullable=False)	# path/whitin/source/pkg
    line = Column(Integer, nullable=False)
    kind = Column(String)	# see `ctags --list-kinds`; unfortunately ctags
        # gives no guarantee of uniformity in kinds, they might be one-lettered
        # or full names, sigh
    language = Column(Enum(*CTAGS_LANGUAGES, name="ctags_languages"))

    def __init__(self, version, tag, path, line, kind, language):
        self.version_id = version.id
        self.tag = tag
        self.path = path
        self.line = line
        self.kind = kind
        self.language = language
    
    # TODO:
    # after refactoring, when we'll have a File table
    # the query to get a list of files containing a list of tags will be simpler
    #
    # def find_files_containing(self, session, ctags, package=None):
    #     """
    #     Returns a list of files containing all the ctags.
        
    #     session: SQLAlchemy session
    #     ctags: [tags]
    #     package: limit search in package
    #     """
    #     results = (session.query(Ctag.path, Ctag.version_id)
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
        
        results = (session.query(Package.name.label("package"),
                                 Version.vnumber.label("version"),
                                 Ctag.path.label("path"),
                                 Ctag.line.label("line"))
                   .filter(Ctag.tag == ctag)
                   .filter(Ctag.version_id == Version.id)
                   .filter(Version.package_id == Package.id)
                   )
        if package is not None:
            results = results.filter(Package.name == package)
        
        #results = results.order_by(Ctag.version_id, Ctag.path)
        count = results.count()
        if slice_ is not None:
            results = results.slice(slice_[0], slice_[1])
        return (count, results.all())

Index('ix_ctags_tags', Ctag.tag,
      postgresql_where=sql_func.length(Ctag.tag) < 100)


class Metric(Base):
    __tablename__ = 'metrics'
    __table_args__ = (UniqueConstraint('sourceversion_id', 'metric'),)

    id = Column(Integer, primary_key=True)
    sourceversion_id = Column(Integer,
                              ForeignKey('versions.id', ondelete="CASCADE"),
                              nullable=False)
    metric = Column(Enum(*METRIC_TYPES, name="metric_types"), nullable=False)
    value = Column("value_", Integer, nullable=False)

    def __init__(self, version, metric, value):
        self.sourceversion_id = version.id
        self.metric = metric
        self.value = value
