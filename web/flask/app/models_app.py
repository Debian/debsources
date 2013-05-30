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
from modules.sourcecode import SourceCodeIterator

from flask import url_for

import os, subprocess, re, magic

class Package_app(models.Package, db.Model):
    @staticmethod
    def get_packages_prefixes():
        """
        returns the packages prefixes (a, b, ..., liba, libb, ..., y, z)
        """
        return packages_prefixes

class Version_app(models.Version, db.Model):
    pass

class InvalidPackageOrVersionError(ValueError):
    pass

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
            
    
    def __init__(self, package, version=None, path_to=None):
        self.package = package
        self.version = version or ""
        self.path_to = path_to or ""
        
        # if it's a package, we check its existence
        if self.version == "":
            try:
                p = Package_app.query.filter(
                    Package_app.name==self.package).first().id
            except:
                raise InvalidPackageOrVersionError("%s" % self.package)
        else: #_get_debian_path also checks the existence
            debian_path = self._get_debian_path(self.package, self.version)
            
            self.sources_path = os.path.join(
                app.config['SOURCES_FOLDER'],
                debian_path,
                self.package, self.version,
                self.path_to)
            
            self.sources_path_static = os.path.join(
                app.config['SOURCES_STATIC'],
                self._get_debian_path(self.package, self.version),
                self.package, self.version,
                self.path_to)
    
    def ispackage(self):
        """ True if self is a package (top folder) """
        return self.version == ""
    
    def isdir(self):
        """ True if self is a directory, False if it's not """
        return os.path.isdir(self.sources_path)
    
    def isfile(self):
        """ True if sels is a file, False if it's not """
        return os.path.isfile(self.sources_path)
    
    def set_mime(self):
        mime = magic.open(magic.MAGIC_MIME)
        mime.load()
        self.mime = mime.file(self.sources_path)
    
    def istextfile(self):
        """ 
        True if self is a text file, False if it's not.
        Sets self.mime
        """
        try:
            self.mime
        except:
            self.set_mime()
        #return 'text' in mime.file(self.sources_path).split(';')[0]
    
        #mime = subprocess.Popen(["file", self.sources_path],
        #                        stdout=subprocess.PIPE).communicate()[0]
        return re.search('text', self.mime) != None

    def get_raw_url(self):
        return self.sources_path_static
    
    def get_path_links(self):
        """
        returns the path hierarchy with urls, to use with 'You are here:'
        [(name, url(name)), (...), ...]
        """
        pathl = []
        pathl.append((self.package, url_for('source', package=self.package)))
        
        if self.version != "":
            pathl.append((self.version, url_for('source', package=self.package,
                                                version=self.version)))
        if self.path_to != "":
            prev_path = ""
            for p in self.path_to.split('/'):
                pathl.append((p, url_for('source', package=self.package,
                                         version=self.version,
                                         path_to=prev_path+p)))
                prev_path += p+"/"
        return pathl

class PackageFolder(Location):
    """
    The top directory of a package
    We use another class to ensure the same layout than a folder when we
    do a package versions listing (e.g. we need get_path_links()
    """
    def __init__(self, package):
        self.p = Package_app.query.filter(Package_app.name==package).first()
        super(PackageFolder, self).__init__(package)
    
    def get_package_name(self):
        """ returns the name of the package """
        return self.package
    
    def get_versions(self):
        """ returns the list of versions of the package """
        return self.p.versions

class Directory(Location):
    """ a folder in a package """
    def _sub_url(self, subfile):
        """ returns the URL of a sub file/folder in this directory """
        if self.version == "":
            return url_for('source', package=self.package, version=subfile)
        elif self.path_to == "":
            return url_for('source', package=self.package,
                           version=self.version, path_to=subfile)
        else:
            return url_for('source', package=self.package,
                           version=self.version,
                           path_to=self.path_to+"/"+subfile)
    
    def get_subdirs(self):
        """ returns the list of the subfolders along with their URLs """
        return sorted((f, self._sub_url(f))
                      for f in os.listdir(self.sources_path)
                      if os.path.isdir(os.path.join(self.sources_path, f)))
    
    def get_subfiles(self):
        """ returns the list of the subfiles along with their URLs """
        return sorted((d, self._sub_url(d))
                      for d in os.listdir(self.sources_path)
                      if os.path.isfile(os.path.join(self.sources_path, d)))
    
    def is_top_folder(self):
        """ True if this is a top folder of a package, False otherwise """
        return self.version == ""

class SourceFile(Location):
    """ a source file in a package """
    def __init__(self, package, version, path_to, highlight, msg):
        super(SourceFile, self).__init__(package, version, path_to)
        self.highlight = highlight
        self.msg = msg
        self.number_of_lines = None
        try:
            self.mime
        except:
            self.set_mime()
        self.file_encoding = self.mime.split("charset=")[-1]
        self.code = SourceCodeIterator(self.sources_path, self.highlight,
                                       encoding=self.file_encoding)
    
    def get_msgdict(self):
        """
        returns a dict(position=, title=, message=) generated from
        the string message (position:title:message)
        """
        if self.msg is None: return dict()
        msgsplit = self.msg.split(':')
        msgdict = dict()
        try:
            msgdict['position'] = int(msgsplit[0])
        except ValueError:
            msgdict['position'] = 1
        try:
            msgdict['title'] = msgsplit[1]
        except IndexError:
            msgdict['title'] = ""
        try:
            msgdict['message'] = ":".join(msgsplit[2:])
        except IndexError:
            msgdict['message'] = ""
        return msgdict
    
    def get_number_of_lines(self):
        if self.number_of_lines is not None:
            return number_of_lines
        number_of_lines = 0
        with open(self.sources_path) as sfile:
            for line in sfile: number_of_lines += 1
        return number_of_lines
    
    def get_code(self):
        return self.code
