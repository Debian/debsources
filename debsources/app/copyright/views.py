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

from flask.views import View

from ..views import GeneralView


# this is just a placeholder
class IndexView(View):

    def dispatch_request(self):
        return "Hello World"


class LicenseView(GeneralView):

    def get_objects(self, path_to):
        path_dict = path_to.split('/')

        package = path_dict[0]
        version = path_dict[1]

        return dict(package=package,
                    version=version)
