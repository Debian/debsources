# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
#               2013  Stefano Zacchiroli <zack@upsilon.cc>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


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


class Http403Error(Exception):
    pass
