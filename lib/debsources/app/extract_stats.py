# Copyright (C) 2014  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING

from __future__ import absolute_import

from debsources import statistics


def extract_stats(filter_suites=None, filename="cache/stats.data"):
    """
    Extracts information from the collected stats.
    If filter_suites is None, all the information are extracted.
    Otherwise suites must be an array of suites names (can contain "total").
    e.g. extract_stats(filter_suites=["total", "debian_wheezy"])
    """
    res = dict()

    stats = statistics.load_metadata_cache(filename)
    for key, value in stats.items():
        splits = key.split(".")
        # if this key/value is in the required suites, we add it
        if filter_suites is None or splits[0] in filter_suites:
            res[key] = value

    return res
