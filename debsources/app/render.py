# Copyright (C) 2013-2015  The Debsources developers <info@sources.debian.net>.
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

import re

Licenses = {
    r'Apache( License)? 2': 'http://opensource.org/licenses/Apache-2.0',
    r'GPL(v|-)?2(\+)?': 'http://opensource.org/licenses/GPL-2.0',
    r'GPL(v|-)?3\+?': 'http://opensource.org/licenses/GPL-3.0',
    r'GPL(v1)?(?!.[2-9])': 'http://opensource.org/licenses/GPL-1.0',
    r'LGPL(v|-)?2\.1': 'http://opensource.org/licenses/LGPL-2.1',
    r'LGPL(v|-)?3\.0': 'http://opensource.org/licenses/LGPL-3.0',
    r'MIT': 'http://opensource.org/licenses/MIT',
    r'M(ozilla)?P(ublic)?L(icense)? 2\.0':
    'http://opensource.org/licenses/MPL-2.0',
    r'CDDL(-)?1\.0': 'http://opensource.org/licenses/CDDL-1.0',
    r'EPL(-)?1\.0': 'http://opensource.org/licenses/EPL-1.0',
    r'BSD( |-)3( |-)?(Clause )?(License)?':
    'http://opensource.org/licenses/BSD-3-Clause',
    r'BSD( |-)2( |-)?(Clause )?(License)?':
    'http://opensource.org/licenses/BSD-2-Clause',
    r'FreeBSD( License)?': 'http://opensource.org/licenses/BSD-2-Clause',
    r'A(cademic )?F(ree )?L(icense)?( |-)?3\.0 (AFL-3.0)':
    'http://opensource.org/licenses/AFL-3.0',
    r'A(daptive )?P(ublic )?L(icense)?( |-)?1(\.0)?':
    'http://opensource.org/licenses/APL-1.0',
    r'A(pple )?P(ublic )?S(ource )?L(icense)?( |-)?2(\.0)?':
    'http://opensource.org/licenses/APSL-2.0',
}


class RenderLicense(object):

    def __init__(self, license, out):
        """ Creates a new Renderer object based on `out`

            Arguments:
            license: a debian.copyright object
            out: the output format used in rendering the license
        """
        if out == 'jinja':
            self.renderer = JinjaRenderer(license)
        else:
            self.renderer = None

    def render_header(self):
        """ Encapsulation of the render_header method
            so that users won't use directly the renderer

        """
        return self.renderer.render_header()

    def render_files(self, base_url=None):
        """ Encapsulation of the render_files method
            so that users won't use directly the renderer

            `base_url` is used to construct links based on the
            globs in the license files.
        """
        return self.renderer.render_files(base_url)

    def render_licenses(self):
        """ Encapsulation of the render_licenses method
            so that users won't use directly the renderer

        """
        return self.renderer.render_licenses()


class JinjaRenderer(object):

    def __init__(self, license):
        """ Initiates a renderer worker that consumes a license
            and gives an html output
        """
        self.license = license

    def render_header(self):
        """ Return all the header attributs

        """
        return self.license.header._RestrictedWrapper__data

    def render_files(self, base_url):
        """ Returns list of File objects. If `base_url` is provided
            then it creates links to base_url+glob
        """
        paragraphs = []
        for par in self.license.all_files_paragraphs():
            globs = []
            for files in par.files:
                globs.append({'files': files,
                              'url': self.create_url(files, base_url)})
            try:
                l = {'license': self.parse_license(par.license.synopsis),
                     'text': par.license.text}
            except AttributeError:
                l = {'license': None,
                     'text': None}
            paragraphs.append({
                'globs': globs,
                'copyright': par.copyright,
                'comment': par.comment,
                'license': l})
        return paragraphs

    def render_licenses(self):
        """ Creates list of licenses with urls

        """
        licenses = []
        for par in self.license.all_license_paragraphs():
            licenses.append({'synopsis': par.license.synopsis,
                             'link': self.match_license(par.license.synopsis),
                             'text': par.license.text,
                             'comment': par.comment})
        return licenses

    def create_url(self, glob="", base=None,):
        # don't create links for hidden folders/files
        if base is None or not re.search('^\.', glob):
            if glob == '*':
                url = base
            else:
                url = base + glob.replace('/*', '/')
            return url
        else:
            return None

    def match_license(self, synopsis):
        """ Matches a `synopsis` with a license and creates a url
        """
        key = filter(lambda x: re.search(x, synopsis) is not None, Licenses)
        if len(key) is not 0:
            return Licenses[key[0]]
        else:
            return None

    def parse_license(self, synopsis):
        """ Parses a license and created links to license texts

        """
        license = []
        if any(keyword in synopsis for keyword in ['and', 'or']):
            licenses = re.split('(, | ?and | ?or )', synopsis)
            for l in licenses:
                link = self.match_license(l)
                if not link:
                    license.append([l, self.anchor_to_license(l)])
                else:
                    license.append([l, link])
        else:
            link = self.match_license(synopsis)
            if not link:
                license.append([synopsis, self.anchor_to_license(synopsis)])
            else:
                license.append([synopsis, link])
        return license

    def anchor_to_license(self, synopsis):
        """ Matches license into a license in the licenses paragraphs and
            creates an anchor link there.

        """
        licenses = [par.license.synopsis
                    for par in self.license.all_license_paragraphs()]
        if synopsis in licenses:
            return '#license-' + str(licenses.index(synopsis))
        else:
            return None
