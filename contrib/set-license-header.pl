#!/usr/bin/perl

use strict;
use warnings;

my $LICENSE = <<EOT;
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD
EOT

while (my $l = <>) {  # before (C) block: verbatim copy
    if ($l =~ /^#\s+This file is part of Debsources/i) {
	last;  # license block found, stop verbatim copy
    }
    print $l;
}

print $LICENSE;

while (my $l = <>) {  # throw away license block
    if ($l =~ /^[^#]/) {
	print $l;
	last;
    }
}

while (my $l = <>) {  # verbatim copy till the end
    print $l;
}
