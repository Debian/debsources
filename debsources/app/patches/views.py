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

from flask import request, current_app

from ..views import GeneralView, session
from debsources.navigation import Location, SourceFile
from debsources.excepts import (Http404ErrorSuggestions, FileOrFolderNotFound,
                                InvalidPackageOrVersionError)
from ..sourcecode import SourceCodeIterator
from . import patches_helper as helper


ACCEPTED_FORMATS = ['3.0 (quilt)',
                    '3.0 (native)']


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
            serie = serie.strip()
            if not serie.startswith('#') or not serie == "":
                patch = serie.rstrip().split(' ')[0]
                try:
                    serie_path, loc = get_sources_path(session, package,
                                                       version,
                                                       current_app.config,
                                                       'debian/patches/' +
                                                       patch)
                    summary = helper.get_file_deltas(serie_path)
                    deltas, deltas_summary = self._parse_file_deltas(summary,
                                                                     package,
                                                                     version)
                    description, bug = helper.get_patch_details(serie_path)
                    patches_info[serie] = dict(deltas=deltas,
                                               summary=deltas_summary,
                                               download=loc.get_raw_url(),
                                               description=description,
                                               bug=bug)
                except (FileOrFolderNotFound, InvalidPackageOrVersionError):
                    patches_info[serie] = dict(summary='Patch does not exist',
                                               description='---',
                                               bug='')
        return patches_info

    def get_objects(self, path_to):
        path_dict = path_to.split('/')
        package = path_dict[0]
        version = path_dict[1]

        if len(path_dict) > 2:
            raise Http404ErrorSuggestions(package, version, '')

        if version == "latest":  # we search the latest available version
            return self._handle_latest_version(request.endpoint,
                                               package, "")

        versions = self.handle_versions(version, package, "")
        if versions:
            redirect_url_parts = [package, versions[-1]]
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
                        path=path_to,
                        patches=[],
                        format='unknown')

        with io.open(source_format, mode='r', encoding='utf-8') as f:
            format_file = f.read()
        if format_file.rstrip() not in ACCEPTED_FORMATS:
            return dict(package=package,
                        version=version,
                        path=path_to,
                        format=format_file,
                        patches=[],
                        supported=False)

        # are there any patches for the package?
        try:
            series, loc = get_sources_path(session, package, version,
                                           current_app.config,
                                           'debian/patches/series')
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            return dict(package=package,
                        version=version,
                        path=path_to,
                        format=format_file,
                        patches=[],
                        supported=True)
        with io.open(series, mode='r', encoding='utf-8') as f:
            series = f.readlines()

        info = self.parse_patch_series(session, package, version,
                                       current_app.config, series)
        if 'api' in request.endpoint:
            return dict(package=package,
                        version=version,
                        format=format_file.rstrip(),
                        patches=[key.rstrip() for key in info.keys()])
        return dict(package=package,
                    version=version,
                    path=path_to,
                    format=format_file,
                    series=info.keys(),
                    patches=info,
                    supported=True)


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
        patch = '/'.join(path_dict[2:])

        if version == "latest":  # we search the latest available version
            return self._handle_latest_version(request.endpoint, package,
                                               'debian/patches/' + patch)

        versions = self.handle_versions(version, package,
                                        'debian/patches/' + patch)
        if versions and version:
            redirect_url_parts = [package, versions[-1]]
            if patch:
                redirect_url_parts.append(patch)
            redirect_url = '/'.join(redirect_url_parts)
            return self._redirect_to_url(request.endpoint, redirect_url,
                                         redirect_code=302)

        try:
            serie_path, loc = get_sources_path(session, package, version,
                                               current_app.config,
                                               'debian/patches/' +
                                               patch.rstrip())
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            raise Http404ErrorSuggestions(package, version,
                                          'debian/patches/' + patch.rstrip())
        if 'api' in request.endpoint:
            summary = helper.get_file_deltas(serie_path)
            description, bug = helper.get_patch_details(serie_path)
            return dict(package=package,
                        version=version,
                        url=loc.get_raw_url(),
                        name=patch,
                        description=description,
                        bug=bug,
                        file_deltas=summary)
        sourcefile = SourceCodeIterator(serie_path)

        return dict(package=package,
                    version=version,
                    nlines=sourcefile.get_number_of_lines(),
                    file_language='diff',
                    code=sourcefile)
