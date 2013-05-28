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


import argparse
import sys, os
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import exists


parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 

from models import Base, Package, Version

def get_engine_session(url, verbose=True):
    engine = create_engine(url, echo=verbose)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session

def sources2db(sources,  db_url, drop=False, verbose=True):
    engine, session = get_engine_session(url, verbose)
    
    if drop:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    
    # v2
    # first we create the set of all packages and the list of (pack, vers)
    packages = set()
    versions = []
    with open(sources) as sfile:
        for line in sfile:
            cols = line.split() # package, version, area, other stuff
            packages.add(cols[0])
            versions.append((cols[0], cols[1], cols[2]))
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
        [dict(vnumber=b, package_id=packids[a], area=c) for a, b, c in versions]
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
    parser.add_argument("--verbose", action="store_true",
                        help="verbose logging (default: be quiet)")
    args = parser.parse_args()
    
    if args.sqlite_file[0] != '/': # relatve path
        url = os.path.abspath(args.sqlite_file)
    else:
        url = args.sqlite_file
    url = "sqlite:///" + url
    
    #os.environ['PYTHONINSPECT'] = 'True'

    sources2db(args.sources, url, drop=True, verbose=args.verbose)
    if args.verbose:
        print("\n")
        print("Execution time: %f s" % (time.time() - start_time))
