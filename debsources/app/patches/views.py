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
import subprocess

from flask import request, current_app

from ..views import GeneralView, session
from debsources.navigation import Location, SourceFile
from debsources.excepts import (Http404ErrorSuggestions, FileOrFolderNotFound,
                                InvalidPackageOrVersionError)
from ..sourcecode import SourceCodeIterator


class SummaryView(GeneralView):

    def _parse_file_deltas(self, summary, package, version):
        """ Parse a file deltas summary to create links to Debsources

        """
        file_deltas = []
        for line in summary.splitlines()[0:-1]:
            filepath, deltas = line.split(' | ')
            file_deltas.append(dict(filepath=filepath.replace(' ', ''),
                                    deltas=deltas))
        deltas_summary = '\n' + summary.splitlines()[-1]
        return file_deltas, deltas_summary

    def parse_patch_series(self, session, package, version, config, series):
        """ Parse a list of patches available in `series` and create a dict
            with important information such as description if it exists, file
            changes.

        """
        patches_info = dict()
        for serie in series:
            try:
                serie_path, loc = get_sources_path(session, package,
                                                   version,
                                                   current_app.config,
                                                   'debian/patches/'
                                                   + serie.rstrip())
                p = subprocess.Popen(["diffstat", "-p1", serie_path],
                                     stdout=subprocess.PIPE)
                summary, err = p.communicate()
                file_deltas, deltas_summary = self._parse_file_deltas(summary,
                                                                      package,
                                                                      version)
                patches_info[serie] = dict(deltas=file_deltas,
                                           summary=deltas_summary,
                                           download=loc.get_raw_url())
            except (FileOrFolderNotFound, InvalidPackageOrVersionError):
                patches_info[serie] = dict(summary='Patch does not exist')
        return patches_info

    def get_objects(self, path_to):
        path_dict = path_to.split('/')
        package = path_dict[0]
        version = path_dict[1]

        path = '/'.join(path_dict[0:])

        if version == "latest":  # we search the latest available version
            return self._handle_latest_version(request.endpoint,
                                               package, path)

        versions = self.handle_versions(version, package, path)
        if versions:
            redirect_url_parts = [package, versions[-1]]
            if path:
                redirect_url_parts.append(path)
            redirect_url = '/'.join(redirect_url_parts)
            return self._redirect_to_url(request.endpoint,
                                         redirect_url, redirect_code=302)

        # identify patch format, accept only 3.0 quilt
        try:
            source_format, loc = get_sources_path(session, package, version,
                                                  current_app.config,
                                                  'debian/source/format')
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            return dict(package=package,
                        version=version,
                        path=path,
                        format='unknown')

        format_file = open(source_format).read()
        if '3.0 (quilt)' not in format_file:
            return dict(package=package,
                        version=version,
                        path=path,
                        format=format_file)

        # are there any patches for the package?
        try:
            series, loc = get_sources_path(session, package, version,
                                           current_app.config,
                                           'debian/patches/series')
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            return dict(package=package,
                        version=version,
                        path=path,
                        format=format_file,
                        patches=0)
        with io.open(series, mode='r', encoding='utf-8') as f:
            series = f.readlines()

        info = self.parse_patch_series(session, package, version,
                                       current_app.config, series)
        return dict(package=package,
                    version=version,
                    path=path,
                    format='3.0 (quilt)',
                    patches=len(series),
                    series=series,
                    patches_info=info)


def get_sources_path(session, package, version, config, path):
    ''' Creates a sources_path. Returns exception when it arises
    '''
    try:
        location = Location(session,
                            config["SOURCES_DIR"],
                            config["SOURCES_STATIC"],
                            package, version, path)
    except (FileOrFolderNotFound, InvalidPackageOrVersionError) as e:
        raise e

    file_ = SourceFile(location)

    sources_path = file_.get_raw_url().replace(
        config['SOURCES_STATIC'],
        config['SOURCES_DIR'],
        1)
    return sources_path, file_


class PatchView(GeneralView):

    def get_objects(self, path_to):
        path_dict = path_to.split('/')
        package = path_dict[0]
        version = path_dict[1]
        patch = path_dict[2]

        try:
            serie_path, loc = get_sources_path(session, package, version,
                                               current_app.config,
                                               'debian/patches/'
                                               + patch.rstrip())
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            raise Http404ErrorSuggestions(package, version, 'debian/patches/'
                                                            + patch.rstrip())
        sourcefile = SourceCodeIterator(serie_path)

        return dict(package=package,
                    version=version,
                    path=path_to,
                    nlines=sourcefile.get_number_of_lines(),
                    file_language='diff',
                    code=sourcefile)
