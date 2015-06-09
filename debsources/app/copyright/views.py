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

from flask import current_app
from debian import copyright

from debsources.navigation import Location, SourceFile
from debsources.excepts import (Http404ErrorSuggestions, FileOrFolderNotFound,
                                InvalidPackageOrVersionError)
from ..views import GeneralView, session
from ..sourcecode import SourceCodeIterator
from ..render import RenderLicense


class LicenseView(GeneralView):

    def get_objects(self, path_to):
        path_dict = path_to.split('/')

        package = path_dict[0]
        version = path_dict[1]
        path = '/'.join(path_dict[2:])

        if version == "latest":  # we search the latest available version
            return self._handle_latest_version(package, path)

        versions = self.handle_versions(version, package, path)
        if versions:
            redirect_url_parts = [package, versions[-1]]
            if path:
                redirect_url_parts.append(path)
            redirect_url = '/'.join(redirect_url_parts)
            return self._redirect_to_url(redirect_url,
                                         redirect_code=302)
        try:
            location = Location(session,
                                current_app.config["SOURCES_DIR"],
                                current_app.config["SOURCES_STATIC"],
                                package, version, 'debian/copyright')
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            raise Http404ErrorSuggestions(package,
                                          version, 'debian/copyright')

        file_ = SourceFile(location)

        sources_path = file_.get_raw_url().replace(
            current_app.config['SOURCES_STATIC'],
            current_app.config['SOURCES_DIR'],
            1)
        with io.open(sources_path, mode='rt', encoding='utf-8') as f:
            # change render function
            try:
                c = copyright.Copyright(f)
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
