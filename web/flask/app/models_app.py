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
from modules.packages_prefixes import packages_prefixes
#from modules.sourcecode import SourceCodeIterator

from flask import url_for

import os, subprocess, magic

class Package_app(models.Package, db.Model):
    @staticmethod
    def get_packages_prefixes():
        """
        returns the packages prefixes (a, b, ..., liba, libb, ..., y, z)
        """
        return packages_prefixes
    
    def to_dict(self):
        return dict(name=self.name)

    
class Version_app(models.Version, db.Model):
    def to_dict(self):
        return dict(vnumber=self.vnumber, area=self.area)

class InvalidPackageOrVersionError(ValueError):
    pass

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
            
    
    def __init__(self, package, version="", path_to=""):
        debian_path = self._get_debian_path(package, version)
        
        self.sources_path = os.path.join(
            app.config['SOURCES_FOLDER'],
            debian_path,
            package, version,
            path_to)
        if not(os.path.exists(self.sources_path)):
            raise FileOrFolderNotFound("%s %s %s" % (package, version, path_to))
        
        self.sources_path_static = os.path.join(
            app.config['SOURCES_STATIC'],
            debian_path,
            package, version,
            path_to)
    
    def is_dir(self):
        """ True if self is a directory, False if it's not """
        return os.path.isdir(self.sources_path)
    
    def is_file(self):
        """ True if sels is a file, False if it's not """
        return os.path.isfile(self.sources_path)
    
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
    
    def __init__(self, location):
        self.sources_path = location.sources_path

    def get_listing(self):
        def get_type(f):
            if os.path.isdir(os.path.join(self.sources_path, f)):
                return "directory"
            else: 
                return "file"
        return sorted(dict(name=f, type=get_type(f))
                      for f in os.listdir(self.sources_path))
    

class SourceFile(object):
    """ a source file in a package """
    def __init__(self, location):
        self.sources_path = location.sources_path
        self.sources_path_static = location.sources_path_static
        self.mime = self._find_mime()
    
    def _find_mime(self):
        mime = magic.open(magic.MIME_TYPE)
        mime.load()
        type = mime.file(self.sources_path)
        mime = magic.open(magic.MIME_ENCODING)
        mime.load()
        encoding = mime.file(self.sources_path)
        return dict(encoding=encoding, type=type)
    
    def get_mime(self):
        return self.mime

    def istextfile(self):
        """ 
        True if self is a text file, False if it's not.
        """
        return re.search('text', self.mime['type']) != None
    
    def get_raw_url(self):
        return self.sources_path_static
