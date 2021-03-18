# Copyright (C) 2021  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING

"""Test paths (custom JSON encoder used by Flask, custom SQLAlchemy type)."""

import json
import unittest
from pathlib import Path

from sqlalchemy import Column, Integer, text
from sqlalchemy.ext.declarative import declarative_base

from debsources.app.json_encoder import Encoder
from debsources.models import PathType
from debsources.tests.db_testing import DbTestFixture
from debsources.tests.test_webapp import DebsourcesBaseWebTests


class PathTestCase(unittest.TestCase):
    """Test custom JSON encoder."""

    def test_json_encode(self):
        test_cases = [
            (Path('/some/filesystem/path/'), '"/some/filesystem/path"'),
            ([Path('some/filesystem.path')], '["some/filesystem.path"]'),
            ({'foo': (Path('a') / 'b').parent}, '{"foo": "a"}')
        ]
        for test_case in test_cases:
            self.assertEqual(Encoder().encode(test_case[0]), test_case[1])


class PathWebTestCase(DebsourcesBaseWebTests, unittest.TestCase):
    """Test Flask did register the custom JSON encoder."""

    def test_json_encode_through_app(self):
        rv = json.loads(self.app.get(
            '/copyright/api/sha256/?checksum='
            'be43f81c20961702327c10e9bd5f5a9a2b1cceea850402ea562a9a76abcfa4bf')
            .data)
        self.assertEqual(len(rv['result']['copyright']), 3)
        for result in rv['result']['copyright']:
            self.assertEqual(result['path'], 'COPYING')


Base = declarative_base()


class EntityWithPath(Base):
    """Fake SQLAlchemy entity that contains a path."""

    __tablename__ = 'entity_with_path'

    id = Column(Integer, primary_key=True)
    path = Column(PathType)


class PathDbTestCase(DbTestFixture, unittest.TestCase):
    """Test SQLAlchemy custom type PathType."""

    @classmethod
    def setUpClass(cls):
        cls.db_setup_cls()
        Base.metadata.create_all(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db_teardown_cls()

    def test_sqlalchemy_path(self):
        for (path, path_bytes) in [
                (Path('/hello') / 'world', b'/hello/world'),
                (Path('\udcff'), b'\xff'),  # non utf8, surrogateescape
        ]:
            # Create and save an EntityWithPath in DB
            entity = EntityWithPath(path=path)
            self.session.add(entity)
            self.session.commit()

            # Retrieve from DB through ORM
            entity_with_path = self.session.query(EntityWithPath).one()
            self.assertEqual(entity_with_path.path, path)

            # Retrieve from DB through SQL
            result = self.session.execute(text('SELECT * FROM entity_with_path;'))
            raw_entity_with_path = list(result)
            self.assertEqual(len(raw_entity_with_path), 1)  # 1 item
            self.assertEqual(
                bytes(raw_entity_with_path[0][1]),  # from memoryview to bytes
                path_bytes
            )

            # Clean up
            self.session.delete(entity)
