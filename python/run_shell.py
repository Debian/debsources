#!/usr/bin/python

import os
import readline
import rlcompleter

from pprint import pprint

import mainlib
import sqla_session

from app import *

PYDIR = os.path.dirname(os.path.abspath(__file__))
ROOTDIR = os.path.dirname(PYDIR)
ETCDIR = os.path.join(ROOTDIR, 'etc')
CONFFILE = os.path.join(ETCDIR, 'config.ini')
__alt_conffile = os.path.join(ETCDIR, 'config.local.ini')
if os.path.exists(__alt_conffile):
    CONFFILE = __alt_conffile

readline.parse_and_bind("tab: complete")
os.environ['PYTHONINSPECT'] = 'True'

conf = mainlib.load_configuration(CONFFILE)
engine, session = sqla_session._get_engine_session(conf['db_uri'])
