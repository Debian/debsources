# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#               2013  Stefano Zacchiroli <zack@upsilon.cc>
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


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def _get_engine_session(url, verbose=True):
    engine = create_engine(url, echo=verbose)
    session = scoped_session(sessionmaker(bind=engine))
    return engine, session


def _close_session(session):
    session.remove()
