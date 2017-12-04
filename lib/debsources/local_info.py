# Copyright (C) 2014  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
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

import os


def read_html(fname):
    """try to read an HTML file and return the contained markup.
    Return None if the file doesn't exist or is empty

    """
    markup = None
    if os.path.isfile(fname):
        with open(fname) as f:
            markup = f.read().strip()
        if not markup:
            markup = None
    return markup


def read_update_ts(fname):
    last_update = None
    try:
        with open(fname) as f:
            last_update = f.readline().strip()
    except IOError:
        last_update = "unknown"
    return last_update
