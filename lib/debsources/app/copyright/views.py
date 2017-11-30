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
from debian import copyright

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

    def get_objects(self, packagename, version):
        try:
            sources_path = helper.get_sources_path(session, packagename,
                                                   version,
                                                   current_app.config)
        except (FileOrFolderNotFound, InvalidPackageOrVersionError) as e:
            if isinstance(e, FileOrFolderNotFound):
                raise Http404MissingCopyright(packagename, version, '')
            else:
                raise Http404ErrorSuggestions(packagename, version, '')

        try:
            c = helper.parse_license(sources_path)
        except Exception:
            # non machine readable license
            sourcefile = SourceCodeIterator(sources_path)
            return dict(package=packagename,
                        version=version,
                        code=sourcefile,
                        dump='True',
                        nlines=sourcefile.get_number_of_lines(),)
        return dict(package=packagename,
                    version=version,
                    dump='False',
                    header=helper.get_copyright_header(c),
                    files=helper.parse_copyright_paragraphs_for_html_render(
                        c, "/src/" + packagename + "/" + version + "/"),
                    licenses=helper.parse_licenses_for_html_render(c))


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
                # parse file
                try:
                    c = helper.parse_license(license_path)
                    l = helper.get_license(f['package'], f['version'],
                                           f['path'], c)
                except copyright.NotMachineReadableError:
                    l = None
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

        page = request.args.get("page", 1, type=int)

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

        try:
            c = helper.parse_license(license_path)
            l = helper.get_license(f.package, f.version, f.path, c)
        except copyright.NotMachineReadableError:
            l = None
        return dict(oracle='debian',
                    path=f.path,
                    package=f.package,
                    version=f.version,
                    license=l,
                    origin=helper.license_url(f.package, f.version))

    def get_objects(self, packagename, version, path_to):
        path = str(path_to)
        if version == 'all':
            files = qry.get_files_by_path_package(session, path,
                                                  packagename).all()
        else:
            files = qry.get_files_by_path_package(session, path, packagename,
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
                        package=packagename,
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
        dual_stats_file = os.path.join(app.config["CACHE_DIR"],
                                       "dual_license.data")
        dual_res = extract_stats(filename=dual_stats_file,
                                 filter_suites=[suite])

        dual_licenses = [license.replace(suite + '.', '') for license
                         in dual_res.keys()]

        info = qry.get_suite_info(session, suite)

        return dict(results=res,
                    licenses=sorted(licenses),
                    dual_results=dual_res,
                    dual_licenses=sorted(dual_licenses),
                    suite=suite,
                    rel_date=str(info.release_date),
                    rel_version=info.version)

    def get_stats(self):

        stats_file = os.path.join(app.config["CACHE_DIR"],
                                  "license_stats.data")
        res = extract_stats(filename=stats_file)

        dual_stats_file = os.path.join(app.config["CACHE_DIR"],
                                       "dual_license.data")
        dual_res = extract_stats(filename=dual_stats_file)
        dual_licenses = [license.replace('overall.', '') for license
                         in dual_res.keys()
                         if 'overall.' in license]

        licenses = [license.replace('overall.', '') for license in res.keys()
                    if 'overall.' in license]
        all_suites = [suite for suite in
                      statistics.suites(session, suites='all')]
        all_suites = all_suites[all_suites.index('squeeze'):]
        return dict(results=res,
                    licenses=sorted(licenses),
                    dual_results=dual_res,
                    dual_licenses=sorted(dual_licenses),
                    suites=all_suites)
