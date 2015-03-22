# Copyright (C) 2014  Stefano Zacchiroli <zack@upsilon.cc>
#
# This file is part of Debsources.

from __future__ import absolute_import

import os

from os.path import abspath

from debsources.tests.testdata import *  # NOQA


def mk_conf(tmpdir):
    """return a debsources updater configuration that works in a temp dir

    for testing purposes

    """
    conf = {
        'bin_dir': abspath(os.path.join(TEST_DIR, '../../bin')),
        'cache_dir': os.path.join(tmpdir, 'cache'),
        'db_uri': 'postgresql:///' + TEST_DB_NAME,
        'single_transaction': 'true',
        'dry_run': False,
        'expire_days': 0,
        'force_triggers': '',
        'hooks': ['sloccount', 'checksums', 'ctags', 'metrics'],
        'mirror_dir': os.path.join(TEST_DATA_DIR, 'mirror'),
        'mirror_archive_dir': os.path.join(TEST_DATA_DIR, 'archive'),
        'backends': set(['hooks.fs', 'hooks', 'fs', 'db', 'hooks.db']),
        'root_dir': abspath(os.path.join(TEST_DIR, '../..')),
        'sources_dir': os.path.join(tmpdir, 'sources'),
        'exclude': [],
    }
    return conf
