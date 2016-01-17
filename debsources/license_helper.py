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
import hashlib
from datetime import datetime

from flask import url_for
from debian import copyright

from debsources.models import Checksum, File, Package, PackageName
from debsources.navigation import Location, SourceFile
from debsources.excepts import MissingCopyrightField

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
    return url_for('.license', packagename=package, version=version)


def get_license(session, package, version, path, license_path=None):
    # if not license_path:
    #     # retrieve license from DB
    #     return qry.get_license_w_path(session, package, version, path)

    # parse license file to get license
    try:
        c = parse_license(license_path)
    except copyright.NotMachineReadableError:
        return None

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


def get_paragraph(c, path):
    return c.find_files_paragraph(path)


def get_copyright_header(copyright):
    """ Return all the header attributs

    """
    return copyright.header._RestrictedWrapper__data


def parse_copyright_paragraphs_html_render(copyright, base_url):
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
        except (AttributeError, ValueError):
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
    if any(keyword in synopsis for keyword in ['with', 'exception']):
        return None
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
    licenses = []
    for par in copyright.all_license_paragraphs():
        try:
            licenses.append(par.license.synopsis)
        except (AttributeError, ValueError):
            pass
    if synopsis in licenses:
        return '#license-' + str(licenses.index(synopsis))
    else:
        return None


def export_copyright_to_spdx(c, package, version, session):
    """ Creates the SPDX document and saves the result in fname

    """

    def create_package_code(session, package, version):
        sha = (session.query(Checksum.sha256.label("sha256"))
               .filter(Checksum.package_id == Package.id)
               .filter(Checksum.file_id == File.id)
               .filter(Package.name_id == PackageName.id)
               .filter(PackageName.name == package)
               .filter(Package.version == version)
               .order_by("sha256")
               ).all()
        sha_values = [sha256[0] for sha256 in sha]
        return hashlib.sha256("".join(sha_values)).hexdigest()

    def create_license_ref(license, count, refs, unknown):
        """ Creates license references and adds it in the specific
            dictionnary. Also adds the non standard licenses in unknown
            licenses.
        """
        if license not in refs.keys() and license is not u'':
            if not match_license(license):
                l_id = 'LicenseRef-' + str(count)
                refs[license] = l_id
                count += 1
                unknown[license] = "LicenseId: " + l_id + \
                                   "\nLicenseName: " + l
            else:
                refs[license] = license
        return refs, unknown, count

    # set upstream name for native packages
    if c.header.upstream_name is not None:
        upstream_name = c.header.upstream_name
    else:
        upstream_name = package
    # find out which are not standard and save SPDX required information
    # Non standard licenses are referenced as LicenseRef-<number>
    refs = dict()
    count = 0
    unknown = dict()
    for par in c.all_files_paragraphs():
        try:
            l = par.license.synopsis
            if any(keyword in l for keyword in ['and', 'or']):
                licenses = re.split(', |and |or ', l)
                for license in licenses:
                    refs, unknown, count = create_license_ref(license.rstrip(),
                                                              count, refs,
                                                              unknown)
            else:
                refs, unknown, count = create_license_ref(l, count,
                                                          refs, unknown)

        except (AttributeError, ValueError):
            pass

    # add the available extracted license text for unknown licenses
    for par in c.all_license_paragraphs():
        try:
            l = par.license.synopsis
            if l in refs.keys() and not match_license(l):
                unknown[l] = "LicenseID: " + refs[l] + \
                             "\nExtractedText: <text>" + \
                             par.license.text + "</text>" + \
                             "\nLicenseName: " + l
        except (AttributeError, ValueError):
            pass

    time = datetime.now()
    now = str(time.date()) + 'T' + str(time.time()).split('.')[0] + 'Z'

    spdx = ["SPDXVersion: SPDX-2.0", "DataLicense:CC0-1.0",
            "SPDXID: SPDXRef-DOCUMENT",
            "Relationship: SPDXRef-DOCUMENT DESCRIBES SPDXRef-Package",
            "DocumentName: " + upstream_name,
            "DocumentNamespace: http://spdx.org/spdxdocs/" +
            "spdx-example-444504E0-4F89-41D3-9A0C-0305E82C3301",
            "LicenseListVersion: 2.0",
            "Creator: Person: Debsources",
            "Creator: Organization: Debsources",
            "Creator: Tool: Debsources",
            "Created: " + now,
            "CreatorComment: <text> This document was created by" +
            "Debsources by parsing the respective debian/copyright" +
            "file of the package provided by the Debian project. You" +
            "may follow these links: http://debian.org/ " +
            "http://sources.debian.net/ to get more information about " +
            "Debian and Debsources. </text>",
            "DocumentComment: <text>This document was created using" +
            "SPDX 2.0, version 2.3 of the SPDX License List.</text>",
            "PackageName: " + upstream_name,
            "SPDXID: SPDXRef-Package",
            "PackageDownloadLocation: NOASSERTION",
            "PackageVerificationCode: " + create_package_code(session,
                                                              package,
                                                              version),
            "PackageLicenseConcluded: NOASSERTION"]
    for value in set(refs.values()):
        spdx.append("PackageLicenseInfoFromFiles: " + value)

    spdx.extend(["PackageLicenseDeclared: NOASSERTION",
                "PackageCopyrightText: NOASSERTION"])
    for files in get_files_spdx(refs, package, version, session, c):
        for item in files:
            spdx.append(str(item))
    for u in unknown:
            spdx.append(unknown[u])
    return spdx


def get_files_spdx(refs, package, version, session, c):
    """ Get all files from the DB for a specific package and version and
        then create a dictionnary for the SPDX entries

    """

    def replace_all(text, dic):
        """ Replace all occurences of the keys in dic by the corresponding
            value
        """
        for i, j in dic.iteritems():
            text = text.replace(i, j)
        return text

    files = (session.query(Checksum.sha256.label("sha256"),
                           File.path.label("path"))
             .filter(Checksum.package_id == Package.id)
             .filter(Checksum.file_id == File.id)
             .filter(Package.name_id == PackageName.id)
             .filter(PackageName.name == package)
             .filter(Package.version == version)
             )

    files_info = []

    for i, f in enumerate(files.all()):
        par = get_paragraph(c, f.path)
        try:
            if not match_license(par.license.synopsis):
                license_concluded = replace_all(par.license.synopsis, refs)
            else:
                license_concluded = par.license.synopsis
        except (AttributeError, ValueError):
            license_concluded = "None"
        # NOASSERTION means that the SPDX generator did not calculate that
        # value.
        sha = 'NOASSERTION' if not f.sha256 else f.sha256
        try:
            files_info.append(["FileName: " + f.path,
                               "SPDXID: SPDX-FILE-REF-" + str(i),
                               "FileChecksum: SHA256: " + sha,
                               "LicenseConcluded: " + license_concluded,
                               "LicenseInfoInFile: NOASSERTION",
                               "FileCopyrightText: <text>" +
                               par.copyright.encode('utf-8') + "</text>"])
        except AttributeError:
            raise MissingCopyrightField(package, version, par.files)
    return files_info
