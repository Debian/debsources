# Copyright (C) 2013-2015  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


import os
from pathlib import Path

from flask import current_app, request, jsonify, url_for

from debsources.excepts import (
    Http403Error, Http404ErrorSuggestions, Http404Error, FileOrFolderNotFound,
    InvalidPackageOrVersionError)
from debsources.consts import SLOCCOUNT_LANGUAGES
from debsources import statistics

from debsources.navigation import (Location, Directory,
                                   SourceFile)

from debsources.url import url_decode, url_encode
import debsources.query as qry
from ..views import GeneralView, app, session
from ..extract_stats import extract_stats
from ..infobox import Infobox
from ..sourcecode import SourceCodeIterator
from ..helper import bind_render, bind_redirect


class StatsView(GeneralView):

    def get_stats_suite(self, suite, **kwargs):
        if suite not in statistics.suites(session, 'all'):
            raise Http404Error()  # security, to avoid suite='../../foo',
            # to include <img>s, etc.
        stats_file = current_app.config["CACHE_DIR"] / "stats.data"
        res = extract_stats(filename=stats_file,
                            filter_suites=["debian_" + suite])
        info = qry.get_suite_info(session, suite)

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    suite=suite,
                    rel_date=str(info.release_date),
                    rel_version=info.version)

    def get_stats(self):
        stats_file = app.config["CACHE_DIR"] / "stats.data"
        res = extract_stats(filename=stats_file)

        all_suites = ["debian_" + x for x in
                      statistics.suites(session, suites='all')]
        release_suites = ["debian_" + x for x in
                          statistics.suites(session, suites='release')]
        devel_suites = ["debian_" + x for x in
                        statistics.suites(session, suites='devel')]

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    all_suites=all_suites,
                    release_suites=release_suites,
                    devel_suites=devel_suites)


# SOURCE (packages, versions, folders, files) #
class SourceView(GeneralView):

    def _render_location(self, package, version, path):
        """
        renders a location page, can be a folder or a file
        """
        try:
            location = Location(session,
                                current_app.config["SOURCES_DIR"],
                                current_app.config["SOURCES_STATIC"],
                                package, version, path)
        except (FileOrFolderNotFound, InvalidPackageOrVersionError):
            raise Http404ErrorSuggestions(package, version, path)

        if location.is_symlink():
            # check if it's secure
            symlink_dest = os.readlink(location.sources_path)
            dest = os.path.normpath(  # absolute, target file
                location.sources_path.parent / symlink_dest
            )
            # note: adding trailing slash because normpath drops them
            if dest.startswith(os.path.normpath(location.version_path) + '/'):
                # symlink is safe; redirect to its destination
                redirect_url = os.path.normpath(
                    location.path_to.parent / symlink_dest
                )
                self.render_func = bind_redirect(url_for(request.endpoint,
                                                 path_to=redirect_url),
                                                 code=301)
                return dict(redirect=redirect_url)
            else:
                raise Http403Error(
                    'insecure symlink, pointing outside package/version/')

        if location.is_dir():  # folder, we list its content
            return self._render_directory(location)

        elif location.is_file():  # file
            return self._render_file(location)

        else:  # doesn't exist
            raise Http404Error(None)

    def _render_directory(self, location):
        """
        renders a directory, lists subdirs and subfiles
        """
        # Convert hidden file patterns to bytes, as they are used to match
        # paths, which are bytes.
        hidden_files = [x.encode('utf8') for x in app.config['HIDDEN_FILES'].split(" ")]
        directory = Directory(location, hidden_files)

        pkg_infos = Infobox(session, location.get_package(),
                            location.get_version()).get_infos()

        content = directory.get_listing()
        path = location.get_path_to()

        if self.d.get('api'):
            self.render_func = jsonify
        else:
            self.render_func = bind_render(
                'sources/source_folder.html',
                subdirs=[x for x in content if x['type'] == "directory"],
                subfiles=[x for x in content if x['type'] == "file"],
                nb_hidden_files=sum(1 for f in content if f['hidden']),
                pathl=qry.location_get_path_links(".source", path),)

        return dict(type="directory",
                    directory=location.get_deepest_element(),
                    package=location.get_package(),
                    version=location.get_version(),
                    content=content,
                    path=str(path),
                    pkg_infos=pkg_infos,
                    )

    def _render_file(self, location):
        """
        renders a file
        """
        file_ = SourceFile(location)
        checksum = file_.get_sha256sum(session)
        number_of_duplicates = (qry.count_files_checksum(session, checksum)
                                .first()[0]
                                )
        pkg_infos = Infobox(session,
                            location.get_package(),
                            location.get_version()).get_infos()
        text_file = file_.istextfile()
        raw_url = file_.get_raw_url()
        path = location.get_path_to()

        if self.d.get('api'):
            self.render_func = jsonify
            return dict(type="file",
                        file=location.get_deepest_element(),
                        package=location.get_package(),
                        version=location.get_version(),
                        mime=file_.get_mime(),
                        raw_url=raw_url,
                        path=str(path),
                        text_file=text_file,
                        stat=qry.location_get_stat(location.sources_path),
                        checksum=checksum,
                        number_of_duplicates=number_of_duplicates,
                        pkg_infos=pkg_infos
                        )
        # prepare the non-api render func
        self.render_func = None
        # more work to do with files
        # as long as 'lang' is in keys, then it's a text_file
        lang = None
        if 'lang' in request.args:
            lang = request.args['lang']
        # if the file is not a text file, we redirect to it
        elif not text_file:
            self.render_func = bind_redirect(raw_url)

        # set render func (non-api form)
        if not self.render_func:
            sources_path = location.sources_path
            # we get the variables for highlighting and message (if they exist)
            try:
                highlight = request.args.get('hl')
            except (KeyError, ValueError, TypeError):
                highlight = None
            try:
                msg = request.args.getlist('msg')
                if msg == "":
                    msg = None  # we don't want empty messages
            except (KeyError, ValueError, TypeError):
                msg = None

            # we preprocess the file with SourceCodeIterator
            sourcefile = SourceCodeIterator(
                sources_path, hl=highlight, msg=msg, lang=lang)

            self.render_func = bind_render(
                self.d['templatename'],
                nlines=sourcefile.get_number_of_lines(),
                pathl=qry.location_get_path_links(".source", path),
                file_language=sourcefile.get_file_language(),
                msgs=sourcefile.get_msgdict(),
                code=sourcefile)

        return dict(type="file",
                    file=url_encode(location.get_deepest_element()),
                    package=location.get_package(),
                    version=location.get_version(),
                    mime=file_.get_mime(),
                    raw_url=raw_url,
                    path=str(path),
                    text_file=text_file,
                    stat=qry.location_get_stat(location.sources_path),
                    checksum=checksum,
                    number_of_duplicates=number_of_duplicates,
                    pkg_infos=pkg_infos
                    )

    def get_objects(self, path_to):
        """
        determines if the dealing object is a package/folder/source file
        and sets this in 'type'
        Package: we want the available versions (db request)
        Directory: we want the subdirs and subfiles (disk listing)
        File: we want to render the raw url of the file
        """
        path_to = url_decode(path_to)

        package, version, *path = path_to.split('/')
        path = Path('/'.join(path))

        return self._render_location(package, version, path)
