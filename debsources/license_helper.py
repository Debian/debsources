# Copyright (C) 2015  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD
from __future__ import absolute_import
import io
import logging

from flask import url_for
from debian import copyright

from debsources.navigation import Location, SourceFile
from debsources.excepts import (FileOrFolderNotFound,
                                InvalidPackageOrVersionError)
# import debsources.query as qry


def get_sources_path(session, package, version, config):
    ''' Creates a sources_path. Returns exception when it arises
    '''
    try:
        location = Location(session,
                            config["SOURCES_DIR"],
                            config["SOURCES_STATIC"],
                            package, version, 'debian/copyright')
    except (FileOrFolderNotFound, InvalidPackageOrVersionError) as e:
        raise e

    file_ = SourceFile(location)

    sources_path = file_.get_raw_url().replace(
        config['SOURCES_STATIC'],
        config['SOURCES_DIR'],
        1)
    return sources_path


def parse_license(sources_path):
    required_fields = ['Format:', 'Files:', 'Copyright:', 'License:']
    d_file = open(sources_path).read()
    if not all(field in d_file for field in required_fields):
        raise Exception
    with io.open(sources_path, mode='rt', encoding='utf-8') as f:
        try:
            c = copyright.Copyright(f)
            return c
        except Exception as e:
            raise e


def license_url(package, version):
    return url_for('.license', path_to=(package + '/' + version))


def get_license(session, package, version, path, license_path=None):
    # if not license_path:
    #     # retrieve license from DB
    #     return qry.get_license_w_path(session, package, version, path)

    # parse license file to get license
    try:
        c = parse_license(license_path)
    except Exception:
        return None

    paragraph = c.find_files_paragraph(path)
    if paragraph:
        try:
            return paragraph.license.synopsis
        except AttributeError:
            logging.warn("Path %s in Package %s with version %s is"
                         " missing a license field" % (path, package,
                                                       version))
            return None
    else:
        return None
