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


from sqlalchemy import Column, ForeignKey, Integer, String, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Package(Base):
    __tablename__ = 'packages'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, unique=True)
    versions = relationship("Version", backref="package")#, lazy="joined")
    
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return self.name


class Version(Base):
    __tablename__ = 'versions'
    
    id = Column(Integer, primary_key=True)
    vnumber = Column(String)
    package_id = Column(Integer, ForeignKey('packages.id'))
    area = Column(String(8)) # main, contrib, nonfree
    
    def __init__(self, vnumber, area="main"):
        self.vnumber = vnumber

    def __repr__(self):
        return self.vnumber
    

Index('ix_versions_package_id_vnumber', Version.package_id, Version.vnumber)
