import argparse
import sys, os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import exists


parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 

from models import Base, Package, Version

def get_engine_session(url):
    engine = create_engine(url, echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session

def sources2db(sources,  db_url, drop=False):
    engine, session = get_engine_session(url)
    
    if drop:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    
    # v2
    # first we create the set of all packages
    packages = set()
    with open(sources) as sfile:
        for line in sfile:
            packages.add(line.split()[0])
    # now the associated dict to work with execute
    packlist = []
    for p in packages:
        packlist.append(dict(name=p))
    packages = None
    Package.__table__.insert(bind=engine).execute(packlist)
    # we get the packages list along with their ids
    packages = session.query(Package).all()
    # we build the dict (package1: id1, ...)
    packids = dict()
    for p in packages:
        packids[p.name] = p.id
    # we build the list [dict(vnumber=.., package_id=..), ..]
    versions = []
    with open(sources) as sfile:
        for line in sfile:
            cols = line.split()
            versions.append(dict(vnumber=cols[1],
                                 package_id=packids[cols[0]]))
    packids = None
    Version.__table__.insert(bind=engine).execute(versions)
            

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
