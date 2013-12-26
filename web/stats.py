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

from models import Metric, SlocCount, SuitesMapping, Version


def size(session, suite=None):
    q = session.query(sql_func.sum(Metric.value)) \
               .filter(Metric.metric == 'size')
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)

    size = q.first()[0]
    if not size:
        size = 0

    return size


def sloccount_lang(session, language, suite=None):
    """query the DB via session and return the LOCS written in language

    return LOCS relative to suite, if given, or DB-wide if not

    """
    q = session.query(sql_func.sum(SlocCount.count)) \
               .filter(SlocCount.language == language)
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)

    count = q.first()[0]
    if not count:
        count = 0

    return count


def sloccount_summary(session, suite=None):
    """query the DB via session and return a per-language summary of LOCS

    return summary relative to suite, if given, or DB-wide if not

    """
    q = session.query(SlocCount.language, sql_func.sum(SlocCount.count))
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)
    q = q.group_by(SlocCount.language)

    return dict(q.all())
