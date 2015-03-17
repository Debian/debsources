#!/usr/bin/perl

# move line "from __future__ import ..." lines past copyright header

use strict;
use warnings;

my @stash = ();

while (my $l = <>) {
    if ($l =~ /^from __future__ import /) {
	push @stash, $l;
    } elsif ($l =~ /^\s*$/ && @stash) {
	print "\n";
	for (@stash) { print; }
	print "\n";
	@stash = ();
    } else {
	print $l;
    }
}
