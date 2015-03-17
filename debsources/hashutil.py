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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import

import hashlib

# should be a multiple of 64 (sha1/sha256's block size)
# FWIW coreutils' sha1sum uses 32768
HASH_BLOCK_SIZE = 32768


def sha1sum(path):
    m = hashlib.sha1()
    with open(path) as f:
        while True:
            chunk = f.read(HASH_BLOCK_SIZE)
            if not chunk:
                break
            m.update(chunk)
    return m.hexdigest()


def sha256sum(path):
    m = hashlib.sha256()
    with open(path) as f:
        while True:
            chunk = f.read(HASH_BLOCK_SIZE)
            if not chunk:
                break
            m.update(chunk)
    return m.hexdigest()
