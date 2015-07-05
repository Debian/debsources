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

from collections import defaultdict, Counter
import os

from flask import current_app, request
from debian.debian_support import version_compare

from debsources.render import RenderLicense
import debsources.license_helper as helper
import debsources.query as qry
import debsources.statistics as statistics
from debsources.excepts import (Http404ErrorSuggestions, FileOrFolderNotFound,
                                InvalidPackageOrVersionError,
                                Http404MissingCopyright, Http404Error)
from ..views import GeneralView, ChecksumView, session, app
from ..sourcecode import SourceCodeIterator
from ..pagination import Pagination
from ..extract_stats import extract_stats


class LicenseView(GeneralView):

    def get_objects(self, path_to):
        path_dict = path_to.split('/')

        package = path_dict[0]
        version = path_dict[1]

        if len(path_dict) > 2:
            raise Http404ErrorSuggestions(package, version, '')

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
                raise Http404MissingCopyright(package, version, '')
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

    def _get_files(self, checksum, package, suite):
        if suite != 'latest':
            files = ChecksumView._files_with_sum(checksum, None,
                                                 package, suite)
        else:
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
        return files

    def _get_license_dict(self, files):
        result = []
        for f in files:
            try:
                # once DB full, remove license path
                try:
                    license_path = helper.get_sources_path(session,
                                                           f['package'],
                                                           f['version'],
                                                           current_app.config)
                except (FileOrFolderNotFound, InvalidPackageOrVersionError):
                    raise Http404ErrorSuggestions(f['package'], f['version'],
                                                  '')
                l = helper.get_license(session, f['package'],
                                       f['version'], f['path'], license_path)
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

    def batch_api(self, checksums, package=None, suite=None):
        results = []
        for sha in checksums:
            files = self._get_files(sha, package, suite)
            if not files:
                results.append(dict(checksum=sha,
                                    copyright=[],
                                    count=0))
            else:
                results.append(dict(count=len(files),
                               checksum=sha,
                               copyright=self._get_license_dict(files)))
        return dict(result=results)

    def get_objects(self, **kwargs):
        if request.method == 'POST':
            checksums = request.form.getlist('checksums')
            package = request.form.get('package') or None
            suite = request.form.get('suite') or None
            return self.batch_api(checksums, package, suite)

        try:
            page = int(request.args.get("page"))
        except:
            page = 1

        checksum = request.args.get("checksum")
        package = request.args.get("package") or None
        suite = request.args.get("suite") or None

        all_files = self._get_files(checksum, package=package, suite=suite)

        if 'api' in request.endpoint:
            d_copyright = self._get_license_dict(all_files)
            if not d_copyright:
                return dict(return_code=404,
                            error='Checksum not found',
                            count=0,
                            result=[])
            return dict(return_code=200,
                        count=len(d_copyright),
                        result=dict(checksum=checksum,
                                    copyright=d_copyright))
        else:
            # count files for pagination
            count = len(all_files)
            offset = int(current_app.config.get("LIST_OFFSET") or 60)
            start = (page - 1) * offset
            end = start + offset
            pagination = Pagination(page, offset, count)

            # slice results
            files = all_files[start:end]

            d_copyright = self._get_license_dict(files)

            # minor stats
            all_d_copyright = self._get_license_dict(all_files)
            counter = Counter([x['license'] for x in all_d_copyright
                              if x['license'] is not None]).most_common()
            licenses = [x[0] for x in counter]
            f_license = [x[0] for x in counter if x[1] is counter[0][1]]

            if package is None or len(all_d_copyright) < 2:
                packages = [x['package'] for x in all_d_copyright]
                counter = Counter(packages).most_common()
                f_package = [x[0] for x in counter if x[1] is counter[0][1]]

                return dict(checksum=checksum,
                            copyright=d_copyright,
                            count=len(all_d_copyright),
                            licenses=licenses,
                            frequent_packages=f_package,
                            frequent_licenses=f_license,
                            pagination=pagination)
            else:
                return dict(checksum=checksum,
                            copyright=d_copyright,
                            count=len(d_copyright),
                            package_filter=True,
                            licenses=set(licenses),
                            frequent_licenses=f_license,
                            pagination=pagination)


class SearchFileView(GeneralView):

    def _license_of_files(self, f):
        # once DB full, remove license path
        try:
            license_path = helper.get_sources_path(session, f.package,
                                                   f.version,
                                                   current_app.config)
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            raise Http404ErrorSuggestions(f.package, f.version, '')
        return dict(oracle='debian',
                    path=f.path,
                    package=f.package,
                    version=f.version,
                    license=helper.get_license(session, f.package,
                                               f.version, f.path,
                                               license_path),
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
        if 'api' in request.endpoint:
            if not files:
                return dict(return_code=404,
                            count=0,
                            error='File not found')
            return dict(return_code=200,
                        count=len(files),
                        result=[dict(checksum=res.checksum,
                                copyright=self._license_of_files(res))
                                for res in files])
        else:
            return dict(count=len(files),
                        path=path,
                        package=package,
                        version=version,
                        result=[dict(checksum=res.checksum,
                                copyright=self._license_of_files(res))
                                for res in files])


class StatsView(GeneralView):

    def get_stats_suite(self, suite, **kwargs):
        if suite not in statistics.suites(session, 'all'):
            raise Http404Error()  # security, to avoid suite='../../foo',
            # to include <img>s, etc.
        stats_file = os.path.join(current_app.config["CACHE_DIR"],
                                  "license_stats.data")
        res = extract_stats(filename=stats_file,
                            filter_suites=[suite])
        licenses = [license.replace(suite + '.', '') for license in res.keys()]
        info = qry.get_suite_info(session, suite)

        return dict(results=res,
                    licenses=sorted(licenses),
                    suite=suite,
                    rel_date=str(info.release_date),
                    rel_version=info.version)

    def get_stats(self):

        stats_file = os.path.join(app.config["CACHE_DIR"],
                                  "license_stats.data")
        res = extract_stats(filename=stats_file)

        licenses = [license.replace('overall.', '') for license in res.keys()
                    if 'overall.' in license]
        all_suites = [x for x in
                      statistics.suites(session, suites='all')]
        all_suites = all_suites[all_suites.index('squeeze'):]

        return dict(results=res,
                    licenses=sorted(licenses),
                    suites=all_suites)
