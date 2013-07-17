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


from sqlalchemy import Column, ForeignKey, Integer, String, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from hashutil import sha1sum, sha256sum


vcs_types = ("arch", "bzr", "cvs", "darcs", "git", "hg", "mtn", "svn")

languages = ("ansic", "cpp", "sh", "xml", "java", "python", "perl", "lisp",
             "fortran", "asm", "php", "cs", "pascal", "ruby", "ml", "erlang",
             "tcl", "objc", "haskell", "ada", "yacc", "f90", "exp", "lex",
             "awk", "jsp", "vhdl", "csh", "sed", "modula3", "cobol")


Base = declarative_base()

class Package(Base):
    """ a source package """
    __tablename__ = 'packages'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("Version", backref="package")#, lazy="joined")
    
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return self.name

class Version(Base):
    """ a version of a source package """
    __tablename__ = 'versions'
    
    id = Column(Integer, primary_key=True)
    vnumber = Column(String)
    package_id = Column(Integer, ForeignKey('packages.id'))
    area = Column(String(8)) # main, contrib, nonfree
    vcs_type = Column(Enum(*vcs_types, name="vcs_types"))
    vcs_url = Column(String)
    vcs_browser = Column(String)
    
    def __init__(self, vnumber, area="main"):
        self.vnumber = vnumber

    def __repr__(self):
        return self.vnumber

Index('ix_versions_package_id_vnumber', Version.package_id, Version.vnumber)


class SuitesMapping(Base):
    """
    Debian suites (squeeze, wheezy, etc) mapping with source package versions
    """
    __tablename__ = 'suitesmapping'
    
    id = Column(Integer, primary_key=True)
    sourceversion_id = Column(Integer, ForeignKey('versions.id'))
    suite = Column(String)
    

class Checksums(Base):
    __tablename__ = 'shasums'

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey('versions.id'))
    path = Column(String)
    sha1 = Column(String(40), index=True)
    sha256 = Column(String(64), index=True)

    def __init__(self, version, path, sha1=None, sha256=None):
        self.version = version
        self.path = path
        
        if not sha1:
            sha1 = sha1sum(path)
        self.sha1 = sha1
        
        if not sha256:
            sha256 = sha256sum(path)
        self.sha256 = sha256

class BinaryPackage(Base):
    __tablename__ = 'binarypackages'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("BinaryVersion", backref="binarypackage")
    
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return self.name

class BinaryVersion(Base):
    __tablename__ = 'binaryversions'
    
    id = Column(Integer, primary_key=True)
    vnumber = Column(String)
    binarypackage_id = Column(Integer, ForeignKey('binarypackages.id'))
    sourceversion_id = Column(Integer, ForeignKey('versions.id'))
    area = Column(String(8)) # main, contrib, nonfree
    
    def __init__(self, vnumber, area="main"):
        self.vnumber = vnumber

    def __repr__(self):
        return self.vnumber

class SlocCount(Base):
    __tablename__ = 'sloccounts'
    
    id = Column(Integer, primary_key=True)
    sourceversion_id = Column(Integer, ForeignKey('versions.id'))
    language = Column(Enum(*languages, name="language_names"))
    count = Column(Integer)
