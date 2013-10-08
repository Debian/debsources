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


# Limit on the maximum key length for Postgres columns which are subject to
# btree indexing. The actual value is 8192, but we play safe and round down.
# This allows to have complete indexes, rather than partial, which would
# require AND ing the index predicate to all queries, for the index to be
# consistently use.
MAX_KEY_LENGTH = 8000

# this list should be kept in sync with
# http://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-VCS-fields
VCS_TYPES = ("arch", "bzr", "cvs", "darcs", "git", "hg", "mtn", "svn")

# this list should be kept in sync with languages supported by sloccount. A
# good start is http://www.dwheeler.com/sloccount/sloccount.html (section
# "Basic concepts"). Others have been added to the Debian package via patches.
SLOCCOUNT_LANGUAGES = (

    # sloccount 2.26 languages
    "ada", "asm", "awk", "sh", "ansic", "cpp", "cs", "csh", "cobol", "exp",
    "fortran", "f90", "haskell", "java", "lex", "lisp", "makefile", "ml",
    "modula3", "objc", "pascal", "perl", "php", "python",
    "ruby", "sed", "sql", "tcl", "yacc",

    # enhancements from Debian patches, version 2.26-5
    "erlang", "jsp", "vhdl", "xml",
)

# this list should be kept in sync with languages supported by (exuberant)
# ctags. See: http://ctags.sourceforge.net/languages.html and the output of
# `ctags --list-languages`
CTAGS_LANGUAGES = (
    'ant', 'asm', 'asp', 'awk', 'basic', 'beta', 'c', 'c++',
    'c#', 'cobol', 'dosbatch', 'eiffel', 'erlang', 'flex', 'fortran', 'go',
    'html', 'java', 'javascript', 'lisp', 'lua', 'make', 'matlab',
    'objectivec', 'ocaml', 'pascal', 'perl', 'php', 'python', 'rexx', 'ruby',
    'scheme', 'sh', 'slang', 'sml', 'sql', 'tcl', 'tex', 'vera', 'verilog',
    'vhdl', 'vim', 'yacc',
)

# TODO uniform CTAGS_* language naming (possibly without blessing any of the
# two, but using a 3rd, Debsources specific, canonical form)

METRIC_TYPES = ("size",)


# debian package areas
AREAS = ["main", "contrib", "non-free"]

# sane (?) default if the package prefix file is not available
PREFIXES_DEFAULT = ['0', '2', '3', '4', '6', '7', '9', 'a', 'b', 'c', 'd', 'e',
                    'f', 'g', 'h', 'i', 'j', 'k', 'l', 'lib3', 'liba', 'libb',
                    'libc', 'libd', 'libe', 'libf', 'libg', 'libh', 'libi',
                    'libj', 'libk', 'libl', 'libm', 'libn', 'libo', 'libp',
                    'libq', 'libr', 'libs', 'libt', 'libu', 'libv', 'libw',
                    'libx', 'liby', 'libz', 'm', 'n', 'o', 'p', 'q', 'r', 's',
                    't', 'u', 'v', 'w', 'x', 'y', 'z']
