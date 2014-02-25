#!/usr/bin/python

import os
from pprint import pprint

import rlcompleter
import readline
readline.parse_and_bind("tab: complete")


#from flask import *
from app import *

os.environ['PYTHONINSPECT'] = 'True'
