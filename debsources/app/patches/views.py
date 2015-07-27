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

from flask import request

from ..views import GeneralView


class SummaryView(GeneralView):

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

        return dict(package=package,
                    version=version)
