# Copyright (C) 2011-2013  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

verbose="1"

info() {
    local msg="$1"
    if [ "$verbose" = "1" ] ; then
	echo -e "$0: I: $msg" >> $logfile
    fi
}

warn() {
    local msg="$1"
    echo -e "$0: W: $msg" >> $logfile
}

err() {
    local msg="$1"
    local code="$2"
    echo -e "$0: E: $msg" >> $logfile
    exit $code
}
