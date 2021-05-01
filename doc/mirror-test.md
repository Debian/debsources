* tests
** bandwidth
   wget -O /dev/null
   http://ftp.XX.debian.org/debian/pool/main/i/iceweasel/xulrunner-21.0-dbg_21.0-1_amd64.deb
** ping
   ping -c 10 ftp.XX.debian.org
* results
** ftp.de.debian.org
*** bandwidth 28,6 MB/s
*** ping 38.931 ms
** ftp.fr.debian.org
*** bandwidth 8,34 MB/s
*** ping 6.516 ms
** ftp.ch.debian.org
*** bandwidth 7,09 MB/s
*** ping 14.733 ms
** ftp.hr.debian.org
*** bandwidth 4,73 MB/s
*** ping 41.887 ms
