# Copyright (C) 2014-2021  The Debsources developers
# <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


from pathlib import Path

from debsources.tests.testdata import TEST_DATA_DIR, TEST_DB_NAME, TEST_DIR


def mk_conf(tmpdir: Path):
    """return a debsources updater configuration that works in a temp dir

    for testing purposes

    """
    conf = {
        "bin_dir": (TEST_DIR.parent.parent.parent / "bin").resolve(),
        "cache_dir": tmpdir / "cache",
        "db_uri": "postgresql:///" + TEST_DB_NAME,
        "single_transaction": "true",
        "dry_run": False,
        "expire_days": 0,
        "force_triggers": "",
        "hooks": ["sloccount", "checksums", "ctags", "metrics", "copyright"],
        "mirror_dir": TEST_DATA_DIR / "mirror",
        "mirror_archive_dir": TEST_DATA_DIR / "archive",
        "backends": set(["hooks.fs", "hooks", "fs", "db", "hooks.db"]),
        "root_dir": TEST_DIR.parent.parent.resolve(),
        "sources_dir": tmpdir / "sources",
        "exclude": [],
    }
    return conf
