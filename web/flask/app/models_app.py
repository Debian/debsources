# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
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


from app import app, db
import models

from flask import url_for

import os, subprocess, magic
from debian.debian_support import version_compare

# sane (?) default if the package prefix file is not available
PREFIXES_DEFAULT = ['0', '2', '3', '4', '6', '7', '9', 'a', 'b', 'c', 'd', 'e',
                    'f', 'g', 'h', 'i', 'j', 'k', 'l', 'lib3', 'liba', 'libb',
                    'libc', 'libd', 'libe', 'libf', 'libg', 'libh', 'libi',
                    'libj', 'libk', 'libl', 'libm', 'libn', 'libo', 'libp',
                    'libq', 'libr', 'libs', 'libt', 'libu', 'libv', 'libw',
                    'libx', 'liby', 'libz', 'm', 'n', 'o', 'p', 'q', 'r', 's',
                    't', 'u', 'v', 'w', 'x', 'y', 'z']

class Package_app(models.Package, db.Model):
    @staticmethod
    def get_packages_prefixes():
        """
        returns the packages prefixes (a, b, ..., liba, libb, ..., y, z)
        """
        try:
            with open(app.config['PKG_PREFIXES_FILE']) as f:
                prefixes = [ l.rstrip() for l in f ]
        except IOError:
            prefixes = PREFIXES_DEFAULT
        return prefixes

    
    @staticmethod
    def list_versions_from_name(packagename):
         try:
             package_id = Package_app.query.filter(
                 Package_app.name==packagename).first().id
         except Exception as e:
             raise InvalidPackageOrVersionError(packagename)
         try:
             versions = Version_app.query.filter(
                 Version_app.package_id==package_id).all()
         except Exception as e:
             raise InvalidPackageOrVersionError(packagename)
         # we sort the versions according to debian versions rules
         versions = sorted(versions, cmp=version_compare)
         return versions
    
    def to_dict(self):
        """
        simply serializes a package (because SQLAlchemy query results
        aren't serializable
        """
        return dict(name=self.name)

    
class Version_app(models.Version, db.Model):
    def to_dict(self):
        """
        simply serializes a package (because SQLAlchemy query results
        aren't serializable
        """
        return dict(vnumber=self.vnumber, area=self.area)

# The package or the version doesn't exist in the DB
class InvalidPackageOrVersionError(ValueError): pass

# The Folder or File doesn't exist in the disk
class FileOrFolderNotFound(Exception): pass

class Location(object):
    """ a location in a package, can be a directory or a file """
    
    def _get_debian_path(self, package, version):
        """
        Returns the Debian path of a package version.
        For example: main/h
                     contrib/libz
        It's the path of a *version*, since a package can have multiple
        versions in multiple areas (ie main/contrib/nonfree).
        """
        try:
            p_id = Package_app.query.filter(
                Package_app.name==package).first().id
            varea = Version_app.query.filter(db.and_(
                        Version_app.package_id==p_id,
                        Version_app.vnumber==version)).first().area
        except:
            # the package or version doesn't exist
            raise InvalidPackageOrVersionError("%s %s" % (package, version))
        
        if package[0:3] == "lib":
            prefix = package[0:4]
        else:
            prefix = package[0]
        return os.path.join(varea, prefix)
            
    
    def __init__(self, package, version="", path=""):
        """ initialises useful attributes """
        debian_path = self._get_debian_path(package, version)
        self.package = package
        self.version = version
        self.path = path
        self.path_to = os.path.join(package, version, path)
        
        self.sources_path = os.path.join(
            app.config['SOURCES_FOLDER'],
            debian_path,
            self.path_to)

        if not(os.path.exists(self.sources_path)):
            raise FileOrFolderNotFound("%s" % (self.path_to))
        
        self.sources_path_static = os.path.join(
            app.config['SOURCES_STATIC'],
            debian_path,
            self.path_to)
    
    def is_dir(self):
        """ True if self is a directory, False if it's not """
        return os.path.isdir(self.sources_path)
    
    def is_file(self):
        """ True if sels is a file, False if it's not """
        return os.path.isfile(self.sources_path)

    def issymlink(self):
        """
        True if a folder/file is a symbolic link file, False if it's not
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
    def get_path_links(endpoint, path_to):
        """
        returns the path hierarchy with urls, to use with 'You are here:'
        [(name, url(name)), (...), ...]
        """
        path_dict = path_to.split('/')
        pathl = []
        for (i, p) in enumerate(path_dict):
            pathl.append((p, url_for(endpoint,
                                     path_to='/'.join(path_dict[:i+1]))))
        return pathl

class Directory(object):
    """ a folder in a package """
    
    def __init__(self, location, toplevel=False):
        # if the directory is a toplevel one, we remove the .pc folder
        self.sources_path = location.sources_path
        self.toplevel = toplevel

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
        listing = sorted(dict(name=f, type=get_type(f))
                         for f in os.listdir(self.sources_path))
        if self.toplevel:
            listing = filter(lambda x: x['name'] != ".pc", listing)
        
        return listing
    

class SourceFile(object):
    """ a source file in a package """
    def __init__(self, location):
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

    def istextfile(self, text_file_mimes):
        """ 
        True if self is a text file, False if it's not.
        """
        for substring in text_file_mimes:
            if substring in self.mime['type']:
                return True
        return False
        
    def get_raw_url(self):
        """ return the raw url on disk (e.g. data/main/a/azerty/foo.bar) """
        return self.sources_path_static
