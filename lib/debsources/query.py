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


from functools import cmp_to_key
from pathlib import Path
import os
import stat

from sqlalchemy import func as sql_func, not_
from collections import namedtuple

from debian.debian_support import version_compare
from debsources.url import url_encode
from debsources.consts import PREFIXES_DEFAULT
from debsources.consts import SUITES
from debsources.excepts import InvalidPackageOrVersionError
from debsources.models import (
    Checksum,
    Ctag,
    File,
    Package,
    PackageName,
    Suite,
    SuiteInfo,
    FileCopyright,
)


LongFMT = namedtuple("LongFMT", ["type", "perms", "size", "symlink_dest"])

""" ORM queries """


def pkg_names_get_packages_prefixes(cache_dir):
    """
    returns the packages prefixes (a, b, ..., liba, libb, ..., y, z)
    cache_dir: the cache directory, usually comes from the app config
    """
    try:
        with (cache_dir / "pkg-prefixes").open() as f:
            prefixes = [l.rstrip() for l in f]
    except IOError:
        prefixes = PREFIXES_DEFAULT
    return prefixes


def pkg_names_list_versions(session, packagename, suite="", suite_order=None):
    """
    return all versions of a packagename. If suite is specified, only
    versions contained in that suite are returned. If suite order is
    specified, then ordering is suite first and then by debian version.
    """

    def compare_with_suite_order(a, b):
        try:
            latest_a = max(suite_order.index(x.lower()) for x in a.suites)
        except ValueError:
            latest_a = -1
        try:
            latest_b = max(suite_order.index(x.lower()) for x in b.suites)
        except ValueError:
            latest_b = -1

        if latest_a == latest_b:
            return version_compare(a.version, b.version)
        else:
            return 1 if latest_a > latest_b else -1

    try:
        name_id = (
            session.query(PackageName)
            .filter(PackageName.name == packagename)
            .first()
            .id
        )
    except Exception:
        raise InvalidPackageOrVersionError(packagename)

    try:
        if not suite:
            if not suite_order:
                versions = (
                    session.query(Package).filter(Package.name_id == name_id).all()
                )
                versions = sorted(versions, key=cmp_to_key(version_compare))
            else:
                versions_w_suites = pkg_names_list_versions_w_suites(
                    session, packagename, as_object=True
                )
                versions = sorted(
                    versions_w_suites, key=cmp_to_key(compare_with_suite_order)
                )
        else:
            versions = (
                session.query(Package)
                .filter(Package.name_id == name_id)
                .filter(sql_func.lower(Suite.suite) == suite)
                .filter(Suite.package_id == Package.id)
                .all()
            )
            versions = sorted(versions, key=cmp_to_key(version_compare))
    except Exception:
        raise InvalidPackageOrVersionError(packagename)
    # we sort the versions according to debian versions rules

    return versions


def pkg_names_list_versions_w_suites(
    session, packagename, suite="", reverse=False, as_object=False
):
    """
    return versions with suites. if suite is provided, then only return
    versions contained in that suite. if as_object is true, the version
    is returned as a Package object with suites list added to it.
    """
    # FIXME a left outer join on (Package, Suite) is more preferred.
    # However, per https://stackoverflow.com/a/997467, custom aggregation
    # function to concatenate the suite names for the group_by should be
    # defined on database connection level.
    versions = pkg_names_list_versions(session, packagename, suite)
    versions_w_suites = []
    try:
        for v in versions:
            suites = session.query(Suite).filter(Suite.package_id == v.id).all()
            # sort the suites according to debsources.consts.SUITES
            # use keyfunc to make it py3 compatible
            suites.sort(key=lambda s: SUITES["all"].index(s.suite))
            suites = [s.suite for s in suites]

            if as_object:
                v.suites = suites
            else:
                v = v.to_dict()
                v["suites"] = suites

            versions_w_suites.append(v)
    except Exception:
        raise InvalidPackageOrVersionError(packagename)

    if reverse:
        versions_w_suites.reverse()

    return versions_w_suites


""" Navigation Queries """


def location_get_path_links(endpoint, path_to: Path):
    """
    returns the path hierarchy with urls, to use with 'You are here:'
    [(name, url(name)), (...), ...]
    """
    path_dict = [url_encode(x) for x in path_to.parts]
    pathl = []

    # we import flask here, in order to permit the use of this module
    # without requiring the user to have flask (e.g. bin/debsources-update
    # can run in another machine without flask, because it doesn't use
    # this method)
    from flask import url_for

    # once more here we verify our endpoint in order to provide a valid url
    # This hack is similar to the one in helper.py in redirect_to_url function

    if endpoint == ".versions":
        for (i, p) in enumerate(path_dict):
            pathl.append(
                (p, url_for(endpoint, packagename="/".join(path_dict[: i + 1])))
            )
    else:
        for (i, p) in enumerate(path_dict):
            pathl.append((p, url_for(endpoint, path_to="/".join(path_dict[: i + 1]))))
    return pathl


def location_get_stat(sources_path):
    """
    Returns the filetype and permissions of the folder/file
    on the disk, unix-styled.
    """
    # When porting to Python3, use stat.filemode directly
    sources_stat = os.lstat(sources_path)
    sources_mode, sources_size = sources_stat.st_mode, sources_stat.st_size
    perm_flags = [
        (stat.S_IRUSR, "r", "-"),
        (stat.S_IWUSR, "w", "-"),
        (stat.S_IXUSR, "x", "-"),
        (stat.S_IRGRP, "r", "-"),
        (stat.S_IWGRP, "w", "-"),
        (stat.S_IXGRP, "x", "-"),
        (stat.S_IROTH, "r", "-"),
        (stat.S_IWOTH, "w", "-"),
        (stat.S_IXOTH, "x", "-"),
    ]
    # XXX these flags should be enough.
    type_flags = [
        (stat.S_ISLNK, "l"),
        (stat.S_ISREG, "-"),
        (stat.S_ISDIR, "d"),
    ]
    # add the file type: d/l/-
    file_type = " "
    for ft, sign in type_flags:
        if ft(sources_mode):
            file_type = sign
            break
    file_perms = ""
    for (flag, do_true, do_false) in perm_flags:
        file_perms += do_true if (sources_mode & flag) else do_false

    file_size = sources_size

    symlink_dest = None
    if file_type == "l":
        symlink_dest = os.readlink(sources_path)

    return LongFMT(file_type, file_perms, file_size, symlink_dest)._asdict()


""" SQLAlchemy queries """


def find_ctag(session, ctag, package=None, slice_=None):
    """
    Returns places in the code where a ctag is found.
         tuple (count, [sliced] results)

    session: an SQLAlchemy session
    ctag: the ctag to search
    package: limit results to package
    """

    results = (
        session.query(
            PackageName.name.label("package"),
            Package.version.label("version"),
            Ctag.file_id.label("file_id"),
            File.path.label("path"),
            Ctag.line.label("line"),
        )
        .filter(Ctag.tag == ctag)
        .filter(Ctag.package_id == Package.id)
        .filter(Ctag.file_id == File.id)
        .filter(Package.name_id == PackageName.id)
    )
    if package is not None:
        results = results.filter(PackageName.name == package)

    results = results.order_by(Ctag.package_id, File.path)
    count = results.count()
    if slice_ is not None:
        results = results.slice(slice_[0], slice_[1])
    results = [
        dict(package=res.package, version=res.version, path=res.path, line=res.line)
        for res in results.all()
    ]
    return (count, results)


def get_suite_info(session, suite, first=None):
    """Return SuiteInfo of a `suite`"""
    return session.query(SuiteInfo).filter(SuiteInfo.name == suite).first()


def count_files_checksum(session, checksum, pkg=None, suite=None):
    """Count files with `checksum`"""
    result = session.query(sql_func.count(Checksum.id)).filter(
        Checksum.sha256 == checksum
    )
    if pkg is not None and pkg is not "":
        result = (
            result.filter(PackageName.name == pkg)
            .filter(Checksum.package_id == Package.id)
            .filter(Package.name_id == PackageName.id)
        )
    if suite is not None and suite is not "":
        result = result.filter(Suite.suite == suite).filter(
            Suite.package_id == Checksum.package_id
        )
    return result


def get_pkg_by_name(session, pkg, suite=None):
    """Returns the package filtered by name `pkg`
    Filter by `suite`

    """
    result = session.query(PackageName).filter_by(name=pkg)

    if suite is not None and suite is not "":
        result = (
            result.filter(sql_func.lower(Suite.suite) == suite)
            .filter(Suite.package_id == Package.id)
            .filter(Package.name_id == PackageName.id)
        )
    return result.first()


def get_pkg_by_similar_name(session, pkg, suite=None):
    """Get non exact package result based on name `pkg`
    Filter by `suite`

    """
    result = (
        session.query(PackageName)
        .filter(sql_func.lower(PackageName.name).contains(pkg.lower()))
        .order_by(PackageName.name)
    )

    if suite is not None and suite is not "":
        return filter_pkg_by_suite(session, result, suite)
    else:
        return result


def filter_pkg_by_suite(session, result, suite):
    """Filter `result` with suite"""
    return (
        result.filter(sql_func.lower(Suite.suite) == suite)
        .filter(Suite.package_id == Package.id)
        .filter(Package.name_id == PackageName.id)
        .order_by(PackageName.name)
    )


def get_files_by_checksum(session, checksum, package=None, suite=None):
    """Returns a list of files whose hexdigest is checksum.
    Filter with package

    """
    results = (
        session.query(
            PackageName.name.label("package"),
            Package.version.label("version"),
            Checksum.file_id.label("file_id"),
            File.path.label("path"),
        )
        .filter(Checksum.sha256 == checksum)
        .filter(Checksum.package_id == Package.id)
        .filter(Checksum.file_id == File.id)
        .filter(Package.name_id == PackageName.id)
    )

    if package is not None and package != "":

        results = results.filter(PackageName.name == package)

    if suite is not None and suite is not "":
        results = results.filter(Suite.suite == suite).filter(
            Suite.package_id == Checksum.package_id
        )

    return results.order_by(PackageName.name, Package.version, File.path)


def get_files_by_path_package(session, path, package, version=None):
    """Return a list of files with a specific `path` and `package`
    Filter with `suite`
    """
    results = (
        session.query(
            File.path.label("path"),
            PackageName.name.label("package"),
            Package.version.label("version"),
            Checksum.sha256.label("checksum"),
        )
        .filter(File.path == path)
        .filter(File.package_id == Package.id)
        .filter(Package.name_id == PackageName.id)
        .filter(PackageName.name == package)
        .filter(Checksum.file_id == File.id)
    )

    if version is not None and version is not "":
        results = results.filter(Package.version == version)

    return results.order_by(PackageName.name, Package.version, File.path)


def get_pkg_filter_prefix(session, prefix, suite=None):
    """Get packages filter by `prefix`"""
    result = session.query(PackageName).filter(
        sql_func.lower(PackageName.name).startswith(prefix)
    )

    if prefix == "l":  # we exclude 'lib*' from the 'l' prefix
        result = result.filter(not_(sql_func.lower(PackageName.name).startswith("lib")))

    result = result.order_by(PackageName.name)

    if suite is not None and suite is not "":
        return filter_pkg_by_suite(session, result, suite)
    else:
        return result


def get_all_packages(session):
    """Get the list of packages"""
    return session.query(PackageName).order_by(PackageName.name)


def count_packages(session):
    """Count the packages"""
    return session.query(PackageName).count()


def get_license_w_path(session, package, version, path):
    """Retrieve license of file using its `path`, `package` and  `version`"""
    result = (
        session.query(FileCopyright.license.label("License"))
        .filter(File.id == FileCopyright.file_id)
        .filter(File.path == path)
        .filter(File.package_id == Package.id)
        .filter(Package.name_id == PackageName.id)
        .filter(PackageName.name == package)
        .filter(Package.version == version)
    ).first()
    if result:
        return result[0]
    else:
        return None


def get_ratio(session, suite=None):
    """Get ratio of machine readable files in `suite`"""
    files = session.query(File.id)
    files_w_license = session.query(FileCopyright.file_id)
    if suite:
        files_w_license = (
            files_w_license.join(File)
            .join(Package)
            .join(Suite)
            .filter(Suite.suite == suite)
        )
        files = files.join(Package).join(Suite).filter(Suite.suite == suite)
    ratio = 1 - (files_w_license.count() / files.count())
    return int(ratio * 100)
