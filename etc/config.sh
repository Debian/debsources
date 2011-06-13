# source this file to get common shell (bash) configuration variables

# Unix group owning sources.d.o archive.  We need to set this explicitly after
# each .dsc extraction, since dpkg-source -x insists in not inheriting group
# from (+s) dirs.
gid="sourcesdo"

# Directories where sources.d.o binaries can be found.
bindir="$root/bin"

# Directories where a Debian source mirror can be found.
mirror_dir="/srv/debian-mirror"

# Directories where extracted Debian source packages will be put.
sources_dir="$root/sources"

