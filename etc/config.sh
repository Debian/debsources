# source this file to get common shell (bash) configuration variables

# Root directory of the Debsources installation
root="/srv/debsources"

# Unix group owning debsources archive.  We need to set this explicitly after
# each .dsc extraction, since dpkg-source -x insists in not inheriting group
# from (+s) dirs.
gid="debsources"

# Directories where debsources binaries can be found.
bindir="${root}/bin"

# Directories where (cached) debsources data can be found.
cachedir="${root}/cache"

# Source mirror configuration
mirror_host="ftp.de.debian.org"
mirror_suites="stable,testing,unstable,experimental"
mirror_sections="main,contrib,non-free"

# Directory where the Debian source mirror will be found.
mirror_dir="/srv/debian-mirror"

# Directories where extracted Debian source packages will be put.
# No trailing slash.
sources_dir="${root}/sources"

# Local cache of available source packages
sources_list="${cachedir}/sources.txt"
sources_map="${cachedir}/webredir.map"
sources_dbm="${cachedir}/webredir.dbm"
sources_sql="${cachedir}/sources.sqlite"
timestamp_file="${cachedir}/last-update"

# Statistics data
raw_stats="${cachedir}/stats.data"
rrd_data="${cachedir}/size.rrd"
rrd_size_graph="${cachedir}/size.png"

lockfile="${root}/ONGOING-UPDATE.pid"

logfile="/var/log/debsources/debsources.log"

# Number of days packages are kept around after having disappeared from the
# mirror. After this delay, they will be removed from the debsources instance
# as well. Set to 0 not to keep them around at all.
expire_days=14

# Set to "yes" to avoid doing any distructive operation on the unpacked source
# tree.  Note: this does not affect the debmirror update pulse, which will be
# executed anyhow.
dry_run="no"
