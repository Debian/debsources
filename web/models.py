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
