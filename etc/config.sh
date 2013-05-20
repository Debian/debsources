# source this file to get common shell (bash) configuration variables

# Unix group owning debsources archive.  We need to set this explicitly after
# each .dsc extraction, since dpkg-source -x insists in not inheriting group
# from (+s) dirs.
gid="debsources"

# Directories where debsources binaries can be found.
bindir="$root/bin"

# Source mirror configuration
mirror_host="ftp.fr.debian.org"
mirror_suites="stable,testing,unstable,experimental"
mirror_sections="main,contrib,non-free"

# Directory where the Debian source mirror will be found.
mirror_dir="/srv/debian-mirror"

# Directories where extracted Debian source packages will be put.
sources_dir="$root/sources"

# Local cache of available source packages
sources_list="${root}/sources.txt"
sources_map="${root}/sources.map"

lockfile="$root/ONGOING-UPDATE.pid"

logfile="/var/log/debsources/debsources.log"

# Set to "yes" to avoid doing any distructive operation on the unpacked source
# tree.  Note: this does not affect the debmirror update pulse, which will be
# executed anyhow.
dry_run="no"
