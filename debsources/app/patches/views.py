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

from flask import request, current_app

from ..views import GeneralView, session
from debsources.excepts import (Http404ErrorSuggestions, FileOrFolderNotFound,
                                InvalidPackageOrVersionError, Http404Error)
import debsources.query as qry
from ..sourcecode import SourceCodeIterator
from . import patches_helper as helper


class VersionsView(GeneralView):
    def get_objects(self, packagename):
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        # we list the version with suites it belongs to
        try:
            versions_w_suites = qry.pkg_names_list_versions_w_suites(
                session, packagename, suite, reverse=True)
        except InvalidPackageOrVersionError:
            raise Http404Error("%s not found" % packagename)
        empty = False
        for i, v in enumerate(versions_w_suites):
            try:
                format_file = helper.get_patch_format(session, packagename,
                                                      v['version'],
                                                      current_app.config)
            except FileOrFolderNotFound:
                format_file = ""
                versions_w_suites[i]['supported'] = False
            if not helper.is_supported(format_file.rstrip()):
                versions_w_suites[i]['supported'] = False
            else:
                versions_w_suites[i]['supported'] = True
                try:
                    series = helper.get_patch_series(session, packagename,
                                                     v['version'],
                                                     current_app.config)
                except (FileOrFolderNotFound, InvalidPackageOrVersionError):
                    series = []
                if len(series) == 0:
                    empty = True
                versions_w_suites[i]['series'] = len(series)

        return dict(type="package",
                    package=packagename,
                    versions=versions_w_suites,
                    path=packagename,
                    suite=suite,
                    is_empty=empty)


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
            if not serie.startswith('#') and not serie == "":
                patch = serie.split(' ')[0]
                try:
                    serie_path, loc = helper.get_sources_path(
                        session, package, version, current_app.config,
                        'debian/patches/' + patch)
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

    def get_objects(self, packagename, version):
        path_to = packagename + '/' + version
        if version == "latest":  # we search the latest available version
            return self._handle_latest_version(request.endpoint,
                                               packagename, "")

        versions = self.handle_versions(version, packagename, "")
        if versions:
            redirect_url_parts = [packagename, versions[-1]]
            redirect_url = '/'.join(redirect_url_parts)
            return self._redirect_to_url(request.endpoint,
                                         redirect_url, redirect_code=302)

        try:
            format_file = helper.get_patch_format(session, packagename,
                                                  version, current_app.config)
        except InvalidPackageOrVersionError:
            raise Http404ErrorSuggestions(packagename, version, '')
        except FileOrFolderNotFound:
                return dict(package=packagename,
                            version=version,
                            path=path_to,
                            patches=[],
                            format='unknown')
        if not helper.is_supported(format_file.rstrip()):
            return dict(package=packagename,
                        version=version,
                        path=path_to,
                        format=format_file,
                        patches=[],
                        supported=False)

        # are there any patches for the package?
        try:
            series = helper.get_patch_series(session, packagename, version,
                                             current_app.config)
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            return dict(package=packagename,
                        version=version,
                        path=path_to,
                        format=format_file,
                        patches=[],
                        supported=True)

        info = self.parse_patch_series(session, packagename, version,
                                       current_app.config, series)
        if 'api' in request.endpoint:
            return dict(package=packagename,
                        version=version,
                        format=format_file.rstrip(),
                        patches=sorted([key.rstrip() for key in info.keys()]))
        return dict(package=packagename,
                    version=version,
                    path=path_to,
                    format=format_file,
                    series=info.keys(),
                    patches=info,
                    supported=True)


class PatchView(GeneralView):

    def get_objects(self, packagename, version, path_to):
        if version == "latest":  # we search the latest available version
            return self._handle_latest_version(request.endpoint, packagename,
                                               'debian/patches/' + path_to)

        versions = self.handle_versions(version, packagename,
                                        'debian/patches/' + path_to)
        if versions and version:
            redirect_url_parts = [packagename, versions[-1]]
            redirect_url_parts.append(path_to)
            redirect_url = '/'.join(redirect_url_parts)
            return self._redirect_to_url(request.endpoint, redirect_url,
                                         redirect_code=302)

        try:
            serie_path, loc = helper.get_sources_path(
                session, packagename, version, current_app.config,
                'debian/patches/' + path_to.rstrip())
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            raise Http404ErrorSuggestions(packagename, version,
                                          'debian/patches/' + path_to.rstrip())
        if 'api' in request.endpoint:
            summary = helper.get_file_deltas(serie_path)
            description, bug = helper.get_patch_details(serie_path)
            return dict(package=packagename,
                        version=version,
                        url=loc.get_raw_url(),
                        name=path_to,
                        description=description,
                        bug=bug,
                        file_deltas=summary)
        sourcefile = SourceCodeIterator(serie_path)

        return dict(package=packagename,
                    version=version,
                    nlines=sourcefile.get_number_of_lines(),
                    file_language='diff',
                    code=sourcefile)
