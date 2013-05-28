# Copyright (C) 2011-2013  Stefano Zacchiroli <zack@upsilon.cc>
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

umask 0002

verbose="1"

info() {
    local msg="$1"
    if [ "$verbose" = "1" ] ; then
	echo "I: $msg"
    fi
}

warn() {
    local msg="$1"
    echo "W: $msg"
}

err() {
    local msg="$1"
    local code="$2"
    echo "E: $msg"
    exit $code
}


stats_period=1000
stats_label=""
stats_total=""
stats_count=""

stats_init() {
    stats_label="$1"
    stats_total="$2"
    stats_count=0
}

stats_print() {
    if [ "$verbose" = "1" ] ; then
	msg="heartbeat: $stats_count"
	if [ -n "$stats_total" ] ; then
	    msg="$msg / $stats_total"
	fi
        info "$msg"
    fi
}

stats_tick() {
    stats_count=$[$stats_count+1]
    if [ $[$stats_count % $stats_period] -eq 0 ] ; then
        stats_print
    fi
}
