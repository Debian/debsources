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

from flask import current_app, url_for
from debian import copyright

from debsources.navigation import Location, SourceFile
from debsources.excepts import (Http404ErrorSuggestions, FileOrFolderNotFound,
                                InvalidPackageOrVersionError)


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


def get_file_paragraph(session, package, version, path):
    """ Retrieves the file paragraph of a `package` `version` `path`

    """
    try:
        sources_path = get_sources_path(session, package, version,
                                        current_app.config)
    except (FileOrFolderNotFound, InvalidPackageOrVersionError):
        raise Http404ErrorSuggestions(package, version, '')

    try:
        c = parse_license(sources_path)
    except Exception:
        return None

    # search for path in globs
    path_dict = path.split('/')
    for par in c.all_files_paragraphs():
        for glob in par.files:
            if glob == path_dict[-1]:
                try:
                    return par
                except AttributeError:
                    logging.warn("Path %s in Package %s with version %s is"
                                 " missing a license field" % (path, package,
                                                               version))
                    return None
    # search for folder/* containing our file
    # search in reverse order as we can have f1/f2/filename
    # where f1/* with license1 and f2/* in another
    for folder in reversed(path_dict):
        for par in c.all_files_paragraphs():
            for glob in par.files:
                if glob.replace('/*', '') == folder:
                    try:
                        return par
                    except AttributeError:
                        logging.warn("Path %s Package %s with version %s is"
                                     " missing a license field" % (path,
                                                                   package,
                                                                   version))
                        return None
    # TODO search for /*
    for par in c.all_files_paragraphs():
        for glob in par.files:
            if glob == '*':
                try:
                    return par
                except AttributeError:
                    logging.warn("Path %s Package %s with version %s is"
                                 " missing a license field" % (path, package,
                                                               version))
                    return None


def get_license(session, package, version, path):
    """ Retrieves the license of a `package` `version` `path`

    """
    par = get_file_paragraph(session, package, version, path)
    if par:
        return par.license.synopsis
    else:
        return None
