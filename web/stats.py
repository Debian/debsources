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

from sqlalchemy import func as sql_func

from models import Metric, SuitesMapping, Version


def size(session, suite=None):
    if not suite:
        size = session.query(sql_func.sum(Metric.value)) \
                      .filter_by(metric='size').first()[0]
    else:
        size = session.query(sql_func.sum(Metric.value)) \
                      .join(Version) \
                      .join(SuitesMapping) \
                      .filter(SuitesMapping.suite == suite) \
                      .first()[0]

    if not size:
        size = 0

    return size
