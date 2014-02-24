# Copyright (C) 2014  Matthieu Caneill <matthieu.caneill@gmail.com>
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


def extract_stats(filter_suites=None, filename="cache/stats.data"):
    """
    Extracts information from the collected stats.
    If filter_suites is None, all the information are extracted.
    Otherwise suites must be an array of suites names (can contain "total").
    e.g. extract_stats(filter_suites=["total", "debian_wheezy"])
    """
    languages = set()
    suites = set()
    res = dict()
    
    with open(filename) as f:
        for line in f:
            try:
                (key, value) = line.split()
            except:
                continue
            try:
                value = int(value)
            except:
                pass
            
            # we extract some information (suites, languages)
            splits = key.split(".")
            if splits[0][:7] == "debian_":
                # we extract suites names
                suites.add(splits[0])
            if len(splits) == 3 and splits[1] == "sloccount":
                # we extract language names
                languages.add(splits[2])
            
            # if this key/value is in the required suites, we add it
            if filter_suites is None or splits[0] in filter_suites:
                res[key] = value
    
    # we use lists instead of sets, because they are JSON-serializable
    return dict(results=res, suites=list(suites), languages=list(languages))


if __name__ == "__main__":
    from pprint import pprint
    pprint(extract_stats(filename="stats.data",
                         filter_suites=["debian_wheezy", "total"]))

                
