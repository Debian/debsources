import os

from flask import current_app, request, jsonify, url_for
from sqlalchemy import func as sql_func
from debian.debian_support import version_compare

from debsources.excepts import (
    Http403Error, Http404ErrorSuggestions, Http404Error, FileOrFolderNotFound,
    InvalidPackageOrVersionError)
from debsources.consts import SLOCCOUNT_LANGUAGES
from debsources import statistics
from debsources.models import (
    PackageName, SourceFile, Checksum, Directory, Location)

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
        stats_file = os.path.join(current_app.config["CACHE_DIR"],
                                  "stats.data")
        res = extract_stats(filename=stats_file,
                            filter_suites=["debian_" + suite])

        return dict(results=res,
                    languages=SLOCCOUNT_LANGUAGES,
                    suite=suite)

    def get_stats(self):
        stats_file = os.path.join(app.config["CACHE_DIR"], "stats.data")
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

    def _render_package(self, packagename, path_to):
        """
        renders the package page (which lists available versions)
        """
        suite = request.args.get("suite") or ""
        suite = suite.lower()
        if suite == "all":
            suite = ""
        # we list the version with suites it belongs to
        try:
            versions_w_suites = PackageName.list_versions_w_suites(
                session, packagename, suite)
        except InvalidPackageOrVersionError:
            raise Http404Error("%s not found" % packagename)

        if self.d.get('api'):
            self.render_func = jsonify
        else:
            self.render_func = bind_render(
                'sources/source_package.html',
                # we simply add pathl (for use with "You are here:")
                pathl=Location.get_path_links('.source', path_to))

        return dict(type="package",
                    package=packagename,
                    versions=versions_w_suites,
                    path=path_to,
                    suite=suite,
                    )

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
                os.path.join(os.path.dirname(location.sources_path),
                             symlink_dest))
            # note: adding trailing slash because normpath drops them
            if dest.startswith(os.path.normpath(location.version_path) + '/'):
                # symlink is safe; redirect to its destination
                redirect_url = os.path.normpath(
                    os.path.join(os.path.dirname(location.path_to),
                                 symlink_dest))

                if self.d.get('api'):
                    self.render_func = bind_redirect(url_for('.api_source',
                                                     path_to=redirect_url))
                else:
                    self.render_func = bind_redirect(url_for('.source',
                                                     path_to=redirect_url))
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
        directory = Directory(location, toplevel=(location.get_path() == ""))

        # (if path == "", then the dir is toplevel, and we don't want
        # the .pc directory)

        pkg_infos = Infobox(session, location.get_package(),
                            location.get_version()).get_infos()

        content = directory.get_listing()
        path = location.get_path_to()

        if self.d.get('api'):
            self.render_func = jsonify
        else:
            self.render_func = bind_render(
                'sources/source_folder.html',
                subdirs=filter(lambda x: x['type'] == "directory", content),
                subfiles=filter(lambda x: x['type'] == "file", content),
                pathl=Location.get_path_links(".source", path),)

        return dict(type="directory",
                    directory=location.get_deepest_element(),
                    package=location.get_package(),
                    content=content,
                    path=path,
                    pkg_infos=pkg_infos,
                    )

    def _render_file(self, location):
        """
        renders a file
        """
        file_ = SourceFile(location)
        checksum = file_.get_sha256sum(session)
        number_of_duplicates = (session.query(sql_func.count(Checksum.id))
                                .filter(Checksum.sha256 == checksum)
                                .first()[0])
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
                        mime=file_.get_mime(),
                        raw_url=raw_url,
                        path=path,
                        text_file=text_file,
                        stat=location.get_stat(location.sources_path),
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
            sources_path = raw_url.replace(
                current_app.config['SOURCES_STATIC'],
                current_app.config['SOURCES_DIR'],
                1)
            # ugly, but better than global variable,
            # and better than re-requesting the db
            # TODO: find proper solution for retrieving souces_path
            # (without putting it in kwargs, we don't want it in
            # json rendering eg)

            # we get the variables for highlighting and message (if they exist)
            try:
                highlight = request.args.get('hl')
            except (KeyError, ValueError, TypeError):
                highlight = None
            try:
                msg = request.args.get('msg')
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
                pathl=Location.get_path_links(".source", path),
                file_language=sourcefile.get_file_language(),
                msg=sourcefile.get_msgdict(),
                code=sourcefile)

        return dict(type="file",
                    file=location.get_deepest_element(),
                    package=location.get_package(),
                    mime=file_.get_mime(),
                    raw_url=raw_url,
                    path=path,
                    text_file=text_file,
                    stat=location.get_stat(location.sources_path),
                    checksum=checksum,
                    number_of_duplicates=number_of_duplicates,
                    pkg_infos=pkg_infos
                    )

    def _handle_latest_version(self, package, path):
        """
        redirects to the latest version for the requested page,
        when 'latest' is provided instead of a version number
        """
        try:
            versions = PackageName.list_versions(session, package)
        except InvalidPackageOrVersionError:
            raise Http404Error("%s not found" % package)
        # the latest version is the latest item in the
        # sorted list (by debian_support.version_compare)
        version = sorted([v.version for v in versions],
                         cmp=version_compare)[-1]

        # avoids extra '/' at the end
        if path == "":
            redirect_url = '/'.join([package, version])
        else:
            redirect_url = '/'.join([package, version, path])

        if self.d.get('api'):
            self.render_func = bind_redirect(url_for('.api_source',
                                             path_to=redirect_url))
        else:
            self.render_func = bind_redirect(url_for('.source',
                                             path_to=redirect_url))

        return dict(redirect=redirect_url)

    def get_objects(self, path_to):
        """
        determines if the dealing object is a package/folder/source file
        and sets this in 'type'
        Package: we want the available versions (db request)
        Directory: we want the subdirs and subfiles (disk listing)
        File: we want to render the raw url of the file
        """
        path_dict = path_to.split('/')

        if len(path_dict) == 1:  # package
            return self._render_package(path_dict[0], path_to)

        else:  # folder or file
            package = path_dict[0]
            version = path_dict[1]
            path = '/'.join(path_dict[2:])

            if version == "latest":  # we search the latest available version
                return self._handle_latest_version(package, path)
            else:
                return self._render_location(package, version, path)
