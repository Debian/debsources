from sqlalchemy import Table, MetaData, Column, ForeignKey, Integer, String, \
    and_
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Sequence

Base = declarative_base()


class Package(Base):
    __tablename__ = 'packages'
    
    id = Column('id', Integer, primary_key=True)
    name = Column('name', String)
    versions = relationship("Version", backref="package")
    
    def __init__(self, name):
        self.name = name
        
    def __repr__(self):
        return self.name

class Version(Base):
    __tablename__ = 'versions'
    
    id = Column('id', Integer, primary_key=True)
    vnumber = Column('vnumber', String)
    package_id = Column(Integer, ForeignKey('packages.id'))
    
    def __init__(self, vnumber):
        self.vnumber = vnumber

    def __repr__(self):
        return self.vnumber
    
