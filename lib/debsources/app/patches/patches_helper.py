# Copyright (C) 2015-2021  The Debsources developers
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
import io
import logging
import re
import subprocess

from debsources.navigation import Location, SourceFile

ACCEPTED_FORMATS = ["3.0 (quilt)", "3.0 (native)"]


def get_patch_details(path):
    """Parse a patch to extract the description and or bug if it exists"""
    with open(path, "r", errors="ignore") as content_file:
        patch = content_file.read()
    # check if subject exists
    keywords = ["description:", "subject:"]
    if not any(key in patch.lower() for key in keywords):
        return ("---", "")
    else:
        # split by --- or +++ (file deltas) and then parse as a tag/value
        # document to extract description or subject or bug
        contents = re.split(r"---|\+\+\+", patch)[0]
        dsc = "---"
        bug = ""
        in_description = False
        # possible fields besides description and subject
        # used to extract multiline descriptions
        fields = [
            "origin:",
            "forwarded:",
            "author:",
            "from:",
            "reviewed-by:",
            "acked-by:",
            "last-update:",
            "applied-upstream:",
            "index:",
            "diff",
            "change-id",
        ]
        for line in contents.split("\n"):
            if "description:" in line.lower() or "subject:" in line.lower():
                dsc = re.split(r"description:|subject:", line.lower())[1] + "\n"
                in_description = True
            elif "bug: #" in line.lower():
                bug = line.lower().split("bug: #")[1]
                in_description = False
            elif any(key in line.lower() for key in fields):
                in_description = False
            elif in_description:
                dsc += line + "\n"
        return (dsc, bug)


def get_file_deltas(serie_path):
    """Get file deltas from a patch using diffstat"""
    p = subprocess.Popen(["diffstat", "-p1", "-f0", serie_path], stdout=subprocess.PIPE)
    summary, err = p.communicate()
    if err:
        logging.warn("Reading file deltas patch: %s, error: %s", serie_path, err)
    return summary


def get_sources_path(session, package, version, config, path):
    """Creates a sources_path. Returns exception when it arises"""
    location = Location(
        session, config["SOURCES_DIR"], config["SOURCES_STATIC"], package, version, path
    )

    file_ = SourceFile(location)

    return location.sources_path, file_


def get_patch_format(session, package, version, config):
    """Retrieves a patch format from /debian/source/format"""
    source_format, loc = get_sources_path(
        session, package, version, config, "debian/source/format"
    )
    with io.open(source_format, mode="r", encoding="utf-8") as f:
        format_file = f.read()
    return format_file.strip()


def is_supported(format_):
    """Determines whether a `_format` is supported"""
    return format_ in ACCEPTED_FORMATS


def get_patch_series(session, package, version, config):
    """Retrieves the patch series from debian/patches/series"""
    series, loc = get_sources_path(
        session, package, version, config, "debian/patches/series"
    )
    with io.open(series, mode="r", encoding="utf-8") as f:
        series = f.readlines()
    return series
