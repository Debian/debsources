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

from datetime import datetime

from debsources.models import Checksum, File, Package, PackageName
from debsources.app.copyright import license_helper as helper

Licenses = {
    r'Apache( License)? 2': 'http://opensource.org/licenses/Apache-2.0',
    r'GPL(v|-)?2(\+)?': 'http://opensource.org/licenses/GPL-2.0',
    r'GPL(-)?3\+': 'http://opensource.org/licenses/GPL-3.0',
    r'GPL(v1)?': 'http://opensource.org/licenses/GPL-1.0',
    r'LGPL(-)?2\.1': 'http://opensource.org/licenses/LGPL-2.1',
    r'LGPL(-)?3\.0': 'http://opensource.org/licenses/LGPL-3.0',
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

    def __init__(self, license, out, fname=None, session=None, package=None,
                 version=None):
        """ Creates a new Renderer object based on `out`

            Arguments:
            license: a debian.copyright object
            out: the output format used in rendering the license
            session package and version are used by the SPDX renderer
        """
        if out == 'jinja':
            self.renderer = JinjaRenderer(license)
        elif out == 'spdx':
            self.renderer = SpdxRenderer(license, fname, session, package,
                                         version)
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

    def render_all(self):
        """ Returns all associated objects with the rendering process

        """
        return self.renderer.render_all()


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
                             'link': match_license(par.license.synopsis),
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

    def parse_license(self, synopsis):
        """ Parses a license and created links to license texts

        """
        license = []
        if any(keyword in synopsis for keyword in ['and', 'or']):
            licenses = re.split('(, | ?and | ?or )', synopsis)
            for l in licenses:
                link = match_license(l)
                if not link:
                    license.append([l, self.anchor_to_license(l)])
                else:
                    license.append([l, link])
        else:
            link = match_license(synopsis)
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


def match_license(synopsis):
    """ Matches a `synopsis` with a license and creates a url
    """
    key = filter(lambda x: re.search(x, synopsis) is not None, Licenses)
    if len(key) is not 0:
        return Licenses[key[0]]
    else:
        return None


class SpdxRenderer(object):

    def __init__(self, license, fname, session, package, version):
        """ Initiates a renderer worker that consumes a license
            and creates a SPDX document.
        """
        self.license = license
        self.fname = fname
        self.session = session
        self.package = package
        self.version = version

    def render_all(self):
        """ Creates the SPDX document and saves the result in fname

        """
        unknown_licenses = []
        license_names = [par.license.synopsis for par
                         in self.license.all_files_paragraphs()]
        # find out which are not standard and save SPDX required information
        count = 0
        license_refs = dict()
        for l in license_names:
            if not match_license(l):
                license_refs[l] = 'LicenseRef-' + str(count)
            else:
                license_refs[l] = 'LicenseRef-' + l
            count += 1
        for par in self.license.all_license_paragraphs():
            if not match_license(par.license.synopsis):
                unknown_licenses.append([{'LicenseID':
                                          license_refs[par.license.synopsis]},
                                         {'ExtractedText': "<text>" +
                                          par.license.text + "</text>"},
                                         {'LicenseName': par.license.synopsis},
                                         {'LicenseComment': par.comment}])
        time = datetime.now()
        now = str(time.date()) + 'T' + str(time.time()).split('.')[0] + 'Z'
        output = [{"SPDXVersion": 'SPDX-2.0'},
                  {"DataLicense": 'CC0-1.0'},
                  {"SPDXID": 'SPDXRef-DOCUMENT'},
                  {"Relationship": 'SPDXRef-DOCUMENT' +
                   ' DESCRIBES SPDXRef-Package'},
                  {"DocumentName": self.license.header.upstream_name},
                  {"DocumentNamespace":
                   'http://spdx.org/spdxdocs/spdx-example-444504E0'
                   '-4F89-41D3-9A0C-0305E82C3301'},
                  {"LicenseListVersion": '2.0'},
                  {"Creator: Person": 'Debian'},
                  {"Creator: Organization": 'DebCopyright ()'},
                  {"Creator: Tool": 'DebCopyright'},
                  {"Created": now},
                  {"CreatorComment": "<text> This package has been shipped in"
                   "source and binary form. The binaries were created with"
                   "gcc 4.5.1 and expect to link to compatible system run"
                   "time libraries. </text>"},
                  {"DocumentComment": "<text>This document was created using"
                   "SPDX 2.0, version 2.3 of the SPDX License List.</text>"},
                  {"PackageName": self.license.header.upstream_name +
                   "SPDXID: SPDXRef-Package"},
                  {"PackageDownloadLocation": 'NOASSERTION'},
                  {"PackageVerificationCode": 'sha256?variant'},
                  {"PackageLicenseConcluded": 'NOASSERTION'},
                  {"PackageLicenseInfoFromFiles": set(license_refs.values())},
                  {"PackageLicenseDeclared": 'NOASSERTION'},
                  {"PackageCopyrightText": 'NOASSERTION'},
                  {"Files": self._get_files(license_refs)},
                  {"unknown": unknown_licenses}]
        return output

    def _get_files(self, license_refs):
        """ Get all files from the DB for a specific package and version and
            then create a dictionnary for the SPDX entries

        """
        files = (self.session.query(Checksum.sha256.label("sha256"),
                                    File.path.label("path"))
                 .filter(Checksum.package_id == Package.id)
                 .filter(Checksum.file_id == File.id)
                 .filter(Package.name_id == PackageName.id)
                 .filter(PackageName.name == self.package)
                 .filter(Package.version == self.version)
                 )
        # mandatory fields in SPDX document as well as optional fields we
        # can retrieve value from d/copyright file
        # NOASSERTION means that the SPDX generator did not calculate that
        # value.
        files_info = []
        for i, f in enumerate(files.all()):
            par = helper.get_file_paragraph(self.session, self.package,
                                            self.version, f.path)
            if not match_license(par.license.synopsis):
                license_concluded = license_refs[par.license.synopsis]
            else:
                license_concluded = f.license.synopsis
            files_info.append([{'FileName': f.path},
                               {'SPDXID': 'SPDX-FILE-REF-' + str(i)},
                               {'FileChecksum': 'SHA1: ' + f.sha256},
                               {'LicenseConcluded': license_concluded},
                               {'LicenseInfoInFile': 'NOASSERTION'},
                               {'LicenseComments': par.comment or None},
                               {'FileCopyrightText': "<text>" +
                               par.copyright.encode('utf-8') + "</text>"}])
        return files_info
