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

def get_engine_session(url, verbose=False):
    engine = create_engine(url, echo=verbose)
    Session = sessionmaker(bind=engine)
    session = Session()
    return engine, session

def generate_prefixes(db_url):
    engine, session = get_engine_session(url)
    prefixes = set()
    packages = session.query(Package).all()
    for p in packages:
        prefixes.add(p.name[0]) # simple character
        if p.name[0:3] == "lib": # lib+simple character
            prefixes.add(p.name[0:4])
    return sorted(prefixes)

def output_python(prefixes):
    sys.stdout.write("packages_prefixes = [")
    for p in prefixes:
        sys.stdout.write("'%s', " % (p))
    sys.stdout.write("]\n")
    
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates packages prefixes \
       (a, b, ..., liba, libb, ..., y, z) from the SQLite db in a Python \
       format. You should output this function to \
       flask/app/modules/packages_prefixes.py")
    parser.add_argument("sqlite_file",
                        help="absolute or relative path to the sqlite file")

    args = parser.parse_args()
    
    if args.sqlite_file[0] != '/': # relative path
        url = os.path.abspath(args.sqlite_file)
    else:
        url = args.sqlite_file
    url = "sqlite:///" + url
    
    #os.environ['PYTHONINSPECT'] = 'True'

    prefixes = generate_prefixes(url)
    output_python(prefixes)
