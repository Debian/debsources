# Copyright (C) 2013-2015  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


import logging
import os
from pathlib import Path

from sqlalchemy import sql

from debsources import db_storage
from debsources import hashutil

from debsources.models import Checksum, File


conf = None

MY_NAME = "checksums"
MY_EXT = "." + MY_NAME


def sums_path(pkgdir: Path) -> Path:
    return Path(str(pkgdir) + MY_EXT)


# maximum number of ctags after which a (bulk) insert is sent to the DB
BULK_FLUSH_THRESHOLD = 100000


def parse_checksums(path):
    """parse sha256 checksums from a file in SHA256SUM(1) format

    i.e. each line is "SHA256  PATH\n"

    yield (sha256, pathlib.Path) pairs
    """
    with open(path, "rb") as checksums:
        for line in checksums:
            line = line.rstrip()
            sha256 = line[0:64].decode()  # checksums are stored as strings
            filepath = Path(line[66:].decode("utf8", "surrogateescape"))
            yield (sha256, filepath)


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug("add-package %s" % pkg)

    sumsfile = sums_path(pkgdir)
    sumsfile_tmp = Path(str(sumsfile) + ".new")

    def emit_checksum(out, relpath, abspath):
        if abspath.is_symlink() or not abspath.is_file():
            # Do not checksum symlinks, if they are not dangling / external we
            # will checksum their target anyhow. Do not check special files
            # either; they shouldn't be there per policy, but they might be
            # (and they are in old releases)
            return
        sha256 = hashutil.sha256sum(bytes(abspath))
        out.write(sha256.encode("ascii") + b"  " + bytes(relpath) + b"\n")

    if "hooks.fs" in conf["backends"]:
        if not sumsfile.exists():  # compute checksums only if needed
            with open(sumsfile_tmp, "wb") as out:
                for relpath in file_table:
                    abspath = pkgdir / relpath
                    emit_checksum(out, relpath, abspath)
            os.rename(sumsfile_tmp, sumsfile)

    if "hooks.db" in conf["backends"]:
        db_package = db_storage.lookup_package(session, pkg["package"], pkg["version"])
        insert_q = sql.insert(Checksum.__table__)
        insert_params = []
        if not session.query(Checksum).filter_by(package_id=db_package.id).first():
            # ASSUMPTION: if *a* checksum of this package has already
            # been added to the db in the past, then *all* of them have,
            # as additions are part of the same transaction
            for (sha256, relpath) in parse_checksums(sumsfile):
                params = {"package_id": db_package.id, "sha256": sha256}
                if file_table:
                    try:
                        file_id = file_table[relpath]
                        params["file_id"] = file_id
                    except KeyError:
                        continue
                else:
                    file_ = (
                        session.query(File)
                        .filter_by(package_id=db_package.id, path=relpath)
                        .first()
                    )
                    if not file_:
                        continue
                    params["file_id"] = file_.id
                insert_params.append(params)
                if len(insert_params) >= BULK_FLUSH_THRESHOLD:
                    session.execute(insert_q, insert_params)
                    session.flush()
                    insert_params = []
            if insert_params:  # source packages shouldn't be empty but...
                session.execute(insert_q, insert_params)
                session.flush()


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug("rm-package %s" % pkg)

    if "hooks.fs" in conf["backends"]:
        sumsfile = sums_path(pkgdir)
        if sumsfile.exists():
            sumsfile.unlink()

    if "hooks.db" in conf["backends"]:
        db_package = db_storage.lookup_package(session, pkg["package"], pkg["version"])
        session.query(Checksum).filter_by(package_id=db_package.id).delete()


def init_plugin(debsources):
    global conf
    conf = debsources["config"]
    debsources["subscribe"]("add-package", add_package, title=MY_NAME)
    debsources["subscribe"]("rm-package", rm_package, title=MY_NAME)
    debsources["declare_ext"](MY_EXT, MY_NAME)
