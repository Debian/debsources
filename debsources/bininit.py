# Copyright (C) 2013  Stefano Zacchiroli <zack@upsilon.cc>
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

import os
import sys


BINDIR = os.path.dirname(os.path.abspath(__file__))
ROOTDIR = os.path.dirname(BINDIR)
PYDIR = os.path.join(ROOTDIR, 'python')
ETCDIR = os.path.join(ROOTDIR, 'etc')
sys.path.insert(0, PYDIR)

DEFAULT_CONFFILE = os.path.join(ETCDIR, 'config.ini')
__alt_conffile = os.path.join(ETCDIR, 'config.local.ini')
if os.path.exists(__alt_conffile):
    DEFAULT_CONFFILE = __alt_conffile
