# Copyright (C) 2013  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def _get_engine_session(url, verbose=True):
    engine = create_engine(url, echo=verbose)
    session = scoped_session(sessionmaker(bind=engine))
    return engine, session


def _close_session(session):
    session.remove()
