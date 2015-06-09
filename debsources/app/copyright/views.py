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

from collections import defaultdict

from flask import current_app, request
from debian.debian_support import version_compare

import debsources.query as qry
from debsources.excepts import (Http404ErrorSuggestions, FileOrFolderNotFound,
                                InvalidPackageOrVersionError)

from ..views import GeneralView, ChecksumView, session
from ..sourcecode import SourceCodeIterator
from ..render import RenderLicense
from . import license_helper as helper


class LicenseView(GeneralView):

    def get_objects(self, path_to):
        path_dict = path_to.split('/')

        package = path_dict[0]
        version = path_dict[1]
        path = '/'.join(path_dict[2:])

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

        try:
            sources_path = helper.get_sources_path(session, package, version,
                                                   current_app.config)
        except (FileOrFolderNotFound, InvalidPackageOrVersionError) as e:
            if isinstance(e, FileOrFolderNotFound):
                raise Http404ErrorSuggestions(package, version,
                                              'debian/copyright')
            else:
                raise Http404ErrorSuggestions(package, version, '')

        try:
            c = helper.parse_license(sources_path)
        except Exception:
            # non machine readable license
            sourcefile = SourceCodeIterator(sources_path)
            return dict(package=package,
                        version=version,
                        code=sourcefile,
                        dump='True',
                        nlines=sourcefile.get_number_of_lines(),)
        renderer = RenderLicense(c, 'jinja')
        return dict(package=package,
                    version=version,
                    dump='False',
                    header=renderer.render_header(),
                    files=renderer.render_files(
                        "/src/" + package + "/" + version + "/"),
                    licenses=renderer.render_licenses())


class ChecksumLicenseView(ChecksumView):

    def _license_of_files(self, checksum, package, suite):
        if suite == 'latest':
            files = ChecksumView._files_with_sum(
                checksum, slice_=None, package=package)
            # find latest version of each package
            dd = defaultdict(list)
            for f in files:
                dd[(f['package'])].append(f)
            files = []
            for package in dd:
                version = sorted([item['version'] for item
                                 in dd[package]],
                                 cmp=version_compare)[-1]
                files.append(filter(lambda f: f['version'] == version,
                                    dd[package])[0])
        else:
            files = ChecksumView._files_with_sum(
                checksum, slice_=None, package=package, suite=suite)
        # Not list comprehension to catch error when d/copyright file is not
        # present in the package.
        result = []
        for f in files:
            try:
                l = helper.get_license(session, f['package'],
                                       f['version'], f['path'])
                result.append(dict(oracle='debian',
                                   path=f['path'],
                                   package=f['package'],
                                   version=f['version'],
                                   license=l,
                                   origin=helper.license_url(f['package'],
                                                             f['version'])))
            except Exception:
                result.append(dict(oracle='debian',
                                   path=f['path'],
                                   package=f['package'],
                                   version=f['version'],
                                   license=None,
                                   origin=helper.license_url(f['package'],
                                                             f['version'])))
        return result

    def get_objects(self, **kwargs):
        checksum = request.args.get("checksum")
        package = request.args.get("package") or None
        suite = request.args.get("suite") or None

        d_copyright = self._license_of_files(checksum, package, suite)

        if len(d_copyright) is 0:
            return dict(return_code=404,
                        error='Checksum not found')
        return dict(return_code=200,
                    result=dict(checksum=checksum,
                                copyright=d_copyright))


class SearchFileView(GeneralView):

    def _license_of_files(self, f):
        return dict(oracle='debian',
                    path=f.path,
                    package=f.package,
                    version=f.version,
                    license=helper.get_license(session, f.package,
                                               f.version, f.path),
                    origin=helper.license_url(f.package, f.version))

    def get_objects(self, path_to):
        path_dict = path_to.split('/')

        package = path_dict[0]
        # can be a version, a suite alias, latest or all
        version = path_dict[1]
        path = str('/'.join(path_dict[2:]))

        if version == 'latest':
            return self._handle_latest_version(request.endpoint,
                                               package, path)
        versions = self.handle_versions(version, package, path)
        if versions:
            redirect_url_parts = [package, versions[-1]]
            if path:
                redirect_url_parts.append(path)

            redirect_url = '/'.join(redirect_url_parts)
            return self._redirect_to_url(request.endpoint, redirect_url,
                                         redirect_code=302)

        if version == 'all':
            files = qry.get_files_by_path_package(session, path, package).all()
        else:
            files = qry.get_files_by_path_package(session, path, package,
                                                  version).all()
        if len(files) is 0:
            return dict(return_code=404,
                        error='File not found')
        return dict(return_code=200,
                    result=[dict(checksum=res.checksum,
                            copyright=self._license_of_files(res))
                            for res in files])
