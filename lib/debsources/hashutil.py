# Copyright (C) 2013  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

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
