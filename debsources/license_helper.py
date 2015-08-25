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
import logging
import re

from flask import url_for
from debian import copyright

from debsources.navigation import Location, SourceFile

# import debsources.query as qry


Licenses = {
    r'Apache-2(\.0)?': 'http://opensource.org/licenses/Apache-2.0',
    r'Apache-1(\.0)?': 'http://opensource.org/licenses/Apache-1.0',
    r'LGPL-2(\.1)?': 'http://opensource.org/licenses/LGPL-2.1',
    r'LGPL-3(\.0)?': 'http://opensource.org/licenses/LGPL-3.0',
    r'^GPL-2(\+)?': 'http://opensource.org/licenses/GPL-2.0',
    r'^GPL-3\+?': 'http://opensource.org/licenses/GPL-3.0',
    r'^GPL-1': 'http://opensource.org/licenses/GPL-1.0',
    r'MPL-2(\.0)?': 'http://opensource.org/licenses/MPL-2.0',
    r'CDDL(-)?': 'http://opensource.org/licenses/CDDL-1.0',
    r'BSD-4-clause': 'http://spdx.org/licenses/BSD-4-Clause',
    r'BSD-3-clause': 'http://opensource.org/licenses/BSD-3-Clause',
    r'BSD-2-clause': 'http://opensource.org/licenses/BSD-2-Clause',
    r'Artistic(-2)?': 'http://opensource.org/licenses/Artistic-2.0',
    r'ISC': 'http://opensource.org/licenses/ISC',
    r'EFL': 'http://opensource.org/licenses/EFL-2.0',
    r'Python': 'http://opensource.org/licenses/Python-2.0',
    r'QPL': 'http://opensource.org/licenses/QPL-1.0',
    r'W3C': 'http://opensource.org/licenses/W3C',
    r'LPPL': 'http://opensource.org/licenses/LPPL-1.3c',
    r'Zope': 'http://opensource.org/licenses/ZPL-2.0',
    r'CC-BY-1\.0': 'http://spdx.org/licenses/CC-BY-1.0',
    r'CC-BY-2\.0': 'http://spdx.org/licenses/CC-BY-2.0',
    r'CC-BY-2\.5': 'http://spdx.org/licenses/CC-BY-2.5',
    r'CC-BY-3\.0': 'http://spdx.org/licenses/CC-BY-3.0',
    r'CC-BY-SA-1\.0': 'http://spdx.org/licenses/CC-BY-SA-1.0',
    r'CC-BY-SA-2\.0': 'http://spdx.org/licenses/CC-BY-SA-2.0',
    r'CC-BY-SA-2\.5': 'http://spdx.org/licenses/CC-BY-SA-2.5',
    r'CC-BY-SA-3\.0': 'http://spdx.org/licenses/CC-BY-SA-3.0',
    r'CC-BY-ND-1\.0': 'http://spdx.org/licenses/CC-BY-ND-1.0',
    r'CC-BY-ND-2\.0': 'http://spdx.org/licenses/CC-BY-ND-2.0',
    r'CC-BY-ND-2\.5': 'http://spdx.org/licenses/CC-BY-ND-2.5',
    r'CC-BY-ND-3\.0': 'http://spdx.org/licenses/CC-BY-ND-3.0',
    r'CC-BY-NC-1\.0': 'http://spdx.org/licenses/CC-BY-NC-1.0',
    r'CC-BY-NC-2\.0': 'http://spdx.org/licenses/CC-BY-NC-2.0',
    r'CC-BY-NC-2\.5': 'http://spdx.org/licenses/CC-BY-NC-2.5',
    r'CC-BY-NC-3\.0': 'http://spdx.org/licenses/CC-BY-NC-3.0',
    r'CC-BY-NC-SA-1\.0': 'http://spdx.org/licenses/CC-BY-NC-SA-1.0',
    r'CC-BY-NC-SA-2\.0': 'http://spdx.org/licenses/CC-BY-NC-SA-2.0',
    r'CC-BY-NC-SA-2\.5': 'http://spdx.org/licenses/CC-BY-NC-SA-2.5',
    r'CC-BY-NC-SA-3\.0': 'http://spdx.org/licenses/CC-BY-NC-SA-3.0',
    r'CC-BY-NC-ND-1\.0': 'http://spdx.org/licenses/CC-BY-NC-ND-1.0',
    r'CC-BY-NC-ND-2\.0': 'http://spdx.org/licenses/CC-BY-NC-ND-2.0',
    r'CC-BY-NC-ND-2\.5': 'http://spdx.org/licenses/CC-BY-NC-ND-2.5',
    r'CC-BY-NC-ND-3\.0': 'http://spdx.org/licenses/CC-BY-NC-ND-3.0',
    r'GFDL-1\.1': 'http://spdx.org/licenses/GFDL-1.1',
    r'GFDL-1\.2': 'http://spdx.org/licenses/GFDL-1.2',
    r'GFDL-1\.3': 'http://spdx.org/licenses/GFDL-1.3',
    r'GFDL-NIV': '#',
    r'GFDL-1\.0': 'http://spdx.org/licenses/GFDL-1.0',
    r'CC0': 'http://spdx.org/licenses/CC0-1.0',
}


def get_sources_path(session, package, version, config):
    ''' Creates a sources_path. Returns exception when it arises
    '''
    location = Location(session,
                        config["SOURCES_DIR"],
                        config["SOURCES_STATIC"],
                        package, version, 'debian/copyright')

    file_ = SourceFile(location)

    sources_path = file_.get_raw_url().replace(
        config['SOURCES_STATIC'],
        config['SOURCES_DIR'],
        1)
    return sources_path


def parse_license(sources_path):
    required_fields = ['Format:', 'Files:', 'Copyright:', 'License:']
    d_file = open(sources_path).read()
    if not all(field in d_file for field in required_fields):
        raise copyright.NotMachineReadableError
    with io.open(sources_path, mode='rt', encoding='utf-8') as f:
        return copyright.Copyright(f)


def license_url(package, version):
    return url_for('.license', path_to=(package + '/' + version))


def get_license(package, version, path, c):
    # if not license_path:
    #     # retrieve license from DB
    #     return qry.get_license_w_path(session, package, version, path)
    paragraph = c.find_files_paragraph(path)
    if paragraph:
        try:
            return paragraph.license.synopsis
        except AttributeError:
            logging.warn("Path %s in Package %s with version %s is"
                         " missing a license field" % (path, package,
                                                       version))
            return None
        except ValueError:
            logging.warn("License of path %s in package %s with version %s has"
                         " multiple lines without quotes" % (path,
                                                             package, version))
            return None
    else:
        return None


def get_copyright_header(copyright):
    """ Return all the header attributs

    """
    return copyright.header._RestrictedWrapper__data


def parse_copyright_paragraphs_for_html_render(copyright, base_url):
    """ Returns list of File objects. If `base_url` is provided
        then it creates links to base_url+glob
    """
    paragraphs = []
    for par in copyright.all_files_paragraphs():
        globs = []
        for files in par.files:
            globs.append({'files': files,
                          'url': create_url(files, base_url)})
        try:
            l = {'license': parse_license_synopsis(copyright,
                                                   par.license.synopsis),
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


def parse_licenses_for_html_render(copyright):
    """ Creates list of licenses with urls
    """
    licenses = []
    for par in copyright.all_license_paragraphs():
        licenses.append({'synopsis': par.license.synopsis,
                         'link': match_license(par.license.synopsis),
                         'text': par.license.text,
                         'comment': par.comment})
    return licenses


def create_url(glob="", base=None,):
    # don't create links for hidden folders/files
    if base is None or not re.search('^\.', glob):
        if glob.count('*') > 0:
            # find deepest folder without *
            parts = glob.split('/')
            index = [parts.index(part) for part in parts
                     if '*' in part][0]
            url = base + '/'.join(parts[0:index])
        else:
            url = base + glob
        return url
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


def parse_license_synopsis(copyright, synopsis):
    """ Parses a license and created links to license texts

    """
    license = []
    if any(keyword in synopsis for keyword in ['and', 'or']):
        licenses = re.split('(, | ?and | ?or )', synopsis)
        for l in licenses:
            link = match_license(l)
            if not link:
                license.append([l, anchor_to_license(copyright, l)])
            else:
                license.append([l, link])
    else:
        link = match_license(synopsis)
        if not link:
            license.append([synopsis, anchor_to_license(copyright, synopsis)])
        else:
            license.append([synopsis, link])
    return license


def anchor_to_license(copyright, synopsis):
    """ Matches license into a license in the licenses paragraphs and
        creates an anchor link there.

    """
    licenses = [par.license.synopsis
                for par in copyright.all_license_paragraphs()]
    if synopsis in licenses:
        return '#license-' + str(licenses.index(synopsis))
    else:
        return None
