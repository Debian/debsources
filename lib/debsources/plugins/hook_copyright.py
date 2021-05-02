# Copyright (C) 2015  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


import io
import logging
import os
from pathlib import Path

from debian import copyright

from debsources import db_storage
from debsources.models import FileCopyright, File
from debsources import license_helper as helper

conf = None

MY_NAME = "copyright"
MY_EXT = "." + MY_NAME


def license_path(pkgdir: Path) -> Path:
    return Path(str(pkgdir) + MY_EXT)


def parse_license_file(path):
    license_list = []
    with open(path, "rb") as licenses:
        for line in licenses:
            fields = line.rstrip().split(b"\t")
            license = fields[0].decode("utf8")
            filename = Path(fields[1].decode("utf8", "surrogateescape"))
            license_list.append((license, filename))
    return license_list


def add_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug("add-package %s" % pkg)

    license_file = license_path(pkgdir)
    license_file_tmp = Path(str(license_file) + ".new")

    try:
        c = helper.parse_license(pkgdir / "debian/copyright")
    except copyright.NotMachineReadableError:
        return

    def emit_license(out, package, version, relpath, copyright):
        """Retrieve license of the file. We use `relpath` as we want the path
        inside the package directory which is used in the d/copyright files
        paragraphs
        """
        synopsis = helper.get_license(package, version, relpath, copyright)
        if synopsis is not None:
            s = b"%s\t%s\n" % (synopsis.encode("utf8"), relpath)
            out.write(s)

    if "hooks.fs" in conf["backends"]:
        if not license_file.exists():  # run license only if needed
            with io.open(license_file_tmp, "wb") as out:
                for relpath in file_table:
                    emit_license(out, pkg["package"], pkg["version"], relpath, c)
            os.rename(license_file_tmp, license_file)

    if "hooks.db" in conf["backends"]:
        db_package = db_storage.lookup_package(session, pkg["package"], pkg["version"])
        if (
            not session.query(FileCopyright)
            .join(File)
            .filter(File.package_id == db_package.id)
            .first()
        ):
            # ASSUMPTION: if *a* license of this package has already been
            # added to the db in the past, then *all* of them have, as
            # additions are part of the same transaction
            licenses = parse_license_file(license_file)
            for (synopsis, path) in licenses:
                if file_table:
                    try:
                        file_id = file_table[path]
                    except KeyError:
                        continue
                else:
                    file_ = (
                        session.query(File)
                        .filter_by(package_id=db_package.id, path=path)
                        .first()
                    )
                    if not file_:
                        continue
                    file_id = file_.id
                license = FileCopyright(file_id, "debian", synopsis)
                session.add(license)


def rm_package(session, pkg, pkgdir, file_table):
    global conf
    logging.debug("rm-package %s" % pkg)

    if "hooks.fs" in conf["backends"]:
        licensefile = license_path(pkgdir)
        if licensefile.exists():
            licensefile.unlink()

    if "hooks.db" in conf["backends"]:
        db_package = db_storage.lookup_package(session, pkg["package"], pkg["version"])

        session.execute(
            "DELETE FROM copyright c "
            "Using files f "
            "WHERE f.package_id = :package "
            "AND c.file_id = f.id",
            {"package": db_package.id},
        )


def init_plugin(debsources):
    global conf
    conf = debsources["config"]
    debsources["subscribe"]("add-package", add_package, title=MY_NAME)
    debsources["subscribe"]("rm-package", rm_package, title=MY_NAME)
    debsources["declare_ext"](MY_EXT, MY_NAME)
