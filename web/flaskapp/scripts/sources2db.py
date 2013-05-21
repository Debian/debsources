import argparse
import sys, os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import exists


parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 

from models import Base, Package, Version

class BadFileError(ValueError): pass
class EmptyFileError(BadFileError): pass

def get_engine_session(url):
    engine = create_engine(url, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session

class GroupVersions(object):
    """ given a sources file, returns an iterator like:
    (package1, [version1, version2, ...])
    (package2, [version1, version2, ...])
    """
    def __init__(self, file):
        self.file = open(file)
    def __iter__(self):
        cols = self.file.readline().split()
        self.package = cols[0]
        self.version = [cols[1]]
        return self
    def next(self):
        if self.file.closed:
            raise StopIteration
        while(True):
            try:
                cols = self.file.readline().split()
                if cols[0] == self.package:
                    self.version.append(cols[1])
                else:
                    ret_p = self.package
                    ret_v = self.version
                    self.package = cols[0]
                    self.version = [cols[1]]
                    return (ret_p, ret_v)
            except IndexError:
                self.file.close()
                return (self.package, self.version)


def sources2db(sources,  db_url, drop=False):
    engine, session = get_engine_session(url)
    
    if drop:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    
    # now we update the db
    for (package, versions) in GroupVersions(sources):
        # if the package doesn't exist yet, we add it,
        # get its id, and add the versions
        if not(session.query(exists().where(
                    Package.name == package)).scalar()):
            session.add(Package(package))
            session.commit()
            package_id = session.query(Package).filter(
                Package.name == package).first().id
            for version in versions:
                version = Version(version)
                version.package_id = package_id
                session.add(version)
        # else we get its id and add the inexisting versions
        else:
            package_id = session.query(Package).filter(
                Package.name == package).first().id
            for version in versions:
                version = Version(version)
                if not(session.query(exists().where(and_(
                                Version.vnumber == version.vnumber,
                                Version.package_id == package_id)))):
                    session.add(version)
    session.commit()
            
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Updates a SQLite base from \
    a sources.txt file")
    parser.add_argument("sqlite_file",
                        help="absolute or relative path to the sqlite file")
    parser.add_argument("sources",
                        help="absolute or relative path to the sources.txt file")
    parser.add_argument("--drop",
                        help="drops the database before", action="store_true")
    args = parser.parse_args()
    
    if args.sqlite_file[0] != '/': # relatve path
        url = os.path.abspath(args.sqlite_file)
    else:
        url = args.sqlite_file
    url = "sqlite:///" + url
    
    #os.environ['PYTHONINSPECT'] = 'True'

    sources2db(args.sources, url, drop=args.drop)
