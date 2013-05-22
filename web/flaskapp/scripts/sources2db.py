import argparse
import sys, os
import time

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
    # first we create the set of all packages and the list of (pack, vers)
    packages = set()
    versions = []
    with open(sources) as sfile:
        for line in sfile:
            cols = line.split() # package, version, other stuff
            packages.add(cols[0])
            versions.append((cols[0], cols[1]))
    # now the associated dict to work with execute
    Package.__table__.insert(bind=engine).execute(
        [dict(name=p) for p in packages]
        )
    # we get the packages list along with their ids(without the joined versions)
    packages = session.query(Package).enable_eagerloads(False).all()
    # we build the dict (package1: id1, ...)
    packids = dict()
    for p in packages:
        packids[p.name] = p.id
    # finally the versions dict to work with execute
    Version.__table__.insert(bind=engine).execute(
        [dict(vnumber=b, package_id=packids[a]) for a, b in versions]
        )
            

if __name__ == "__main__":
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Updates a SQLite base from \
    a sources.txt file")
    parser.add_argument("sqlite_file",
                        help="absolute or relative path to the sqlite file")
    parser.add_argument("sources",
                        help="absolute or relative path to the sources.txt file")
    #parser.add_argument("--drop",
    #                    help="drops the database before", action="store_true")
    args = parser.parse_args()
    
    if args.sqlite_file[0] != '/': # relatve path
        url = os.path.abspath(args.sqlite_file)
    else:
        url = args.sqlite_file
    url = "sqlite:///" + url
    
    #os.environ['PYTHONINSPECT'] = 'True'

    sources2db(args.sources, url, drop=True)
    print("\n")
    print("Execution time: %f s" % (time.time() - start_time))
