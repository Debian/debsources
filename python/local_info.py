# Copyright (C) 2014  Stefano Zacchiroli <zack@upsilon.cc>
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

def read_news(fname):
    """try to read an HTML news file and return either the contained markup.
    Return None if the file doesn't exist or is empty

    """
    markup = None
    if os.path.isfile(fname):
        with open(fname) as f:
            markup = f.read().strip()
        if not markup:
            markup = None
    return markup
