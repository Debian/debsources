# Ideas for internships, GSoC, Outreach, and friends

(for inspiration, the open bugs are listed at http://deb.li/debsrcbugs)

## Debsources on Mobile

Enabling Debsources to work on mobile browsers, via an hybrid
(desktop/mobile) design, is an interesting and useful challenge. A
library such as Bootstrap should be used. Additionally, the interface
could be more dynamic, using ajax requests, and libraries such as
jQuery and Angular. An SPA (single page application) would be very
handy, keeping in mind compatibility with text-based javascriptless
browsers is needed.

On a second level, a native app could be developed, leveraging some
new possibilities (saving files, editing them and producing patches (like
with the browser extension), etc). There is a design challenge
involved here, and also a technology choice (e.g. Cordova/PhoneGap
vs. real native).

## Support of other operating systems

Support of security.debian.org, and other operating systems, poses few
challenges:

- refactoring (adding a table for the different archives, changing
  primary keys, lots of UI changes, etc).
- support of the updates coming from different archives through
  different protocols.
- disk size: implement deduplication, at either block or file level
  (see btrfs, mongodb/gridfs), or by hand through the files table and
  its checksums. This can be done:
  - through hard links at update time
  - through hard links via a cronjob (involving race conditions and
    similar challenges).

## Support of other hashing algorithms

In the files table, we currently only compute the sha256 sum. It would
be interesting to have other checksums.

## Integrated sources editor

Raphael Geissert has developed a Firefox/Chrome plugin to allow the
edition of a file directly in Debsources, and to generate a patch
ready to be sent to the maintainer of the modified package.
See http://rgeissert.blogspot.fr/2015/08/updates-to-sourcesdebiannet-editor.html
It would be awesome to:

- integrate it in Debsources' code base, so that users don't require
  to install the browser extension,
- and improve it to support e.g. multi-file editing (that needs
  session management) and/or other features.
