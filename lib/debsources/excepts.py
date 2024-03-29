# Copyright (C) 2013-2021  The Debsources developers
# <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING


class InvalidPackageOrVersionError(ValueError):
    """The package or the version doesn't exist in the DB"""

    pass


class FileOrFolderNotFound(Exception):
    """The Folder or File doesn't exist in the disk"""

    pass


class Http500Error(Exception):
    pass


class Http404Error(Exception):
    pass


class Http404ErrorSuggestions(Http404Error):
    def __init__(self, package, version, path):
        self.package = package
        self.version = version
        self.path = path
        super(Http404ErrorSuggestions, self).__init__()


class Http404MissingCopyright(Http404Error):
    def __init__(self, package, version, path):
        self.package = package
        self.version = version
        self.path = path
        super(Http404MissingCopyright, self).__init__()


class Http403Error(Exception):
    pass
