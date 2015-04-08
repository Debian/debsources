# Copyright (C) 2013  The Debsources developers <info@sources.debian.net>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=AUTHORS;hb=HEAD
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://anonscm.debian.org/gitweb/?p=qa/debsources.git;a=blob;f=COPYING;hb=HEAD

from __future__ import absolute_import

import re

import six
from six.moves import range

# Languages constants
(PYTHON, RUBY, PERL, PHP, SCALA, GO, XML, HTML, MARKDOWN, CSS, JSON,
 JAVASCRIPT, COFFEESCRIPT, ACTIONSCRIPT, VBSCRIPT, LUA, JAVA, C, CPP,
 OBJECTIVEC, VALA, CSHARP, D, SQL, LISP, CLOJURE, INI, APACHE, CMAKE, VHDL,
 DIFF, BASH, TEX, BRAINFUCK, HASKELL, ERLANG, RUST, R, OCAML, SCILAB,
 MAKEFILE) \
    = list(range(41))

# Languages strings used by highlight.js
highlightjs = {
    PYTHON: "python",
    RUBY: "ruby",
    PERL: "perl",
    PHP: "php",
    SCALA: "scala",
    GO: "go",
    XML: "xml",
    HTML: "django",
    MARKDOWN: "markdown",
    CSS: "css",
    JSON: "json",
    JAVASCRIPT: "javascript",
    COFFEESCRIPT: "coffeescript",
    ACTIONSCRIPT: "actionscript",
    VBSCRIPT: "vbscript",
    LUA: "lua",
    JAVA: "java",
    C: "cpp",
    CPP: "cpp",
    OBJECTIVEC: "objectivec",
    VALA: "vala",
    CSHARP: "cs",
    D: "d",
    SQL: "sql",
    LISP: "lisp",
    CLOJURE: "clojure",
    INI: "ini",
    APACHE: "apache",
    CMAKE: "cmake",
    VHDL: "vhdl",
    DIFF: "diff",
    BASH: "bash",
    TEX: "tex",
    BRAINFUCK: "brainfuck",
    HASKELL: "haskell",
    ERLANG: "erlang",
    RUST: "rust",
    R: "r",
    OCAML: "ocaml",
    SCILAB: "scilab",
    MAKEFILE: "makefile",
    }

# Filename regexes
filename_regexes = [
    (PYTHON, [r'\.py$', r'\.pyw$']),
    (RUBY, [r'\.rb$', r'\.rhtml$', r'\.ruby$']),
    (PERL, [r'\.pl$', r'\.PL$', r'\.pm$', r'\.PM$', r'\.perl$', r'\.agi$',
            r'\.pod$']),
    (PHP, [r'\.php[3-6]?$', r'\.phtml$']),
    (SCALA, [r'\.scala$']),
    (GO, [r'\.go$']),
    (XML, [r'\.xml$', r'\.sgml$', r'\.xsl$', r'\.xslt$', r'\.xsd$']),
    (HTML, [r'\.htm$', r'\.html$', r'\.shtml$', r'\.hta$', r'\.htd$',
            r'\.htt$', r'\.cfm$', r'\.xhtml$']),
    (MARKDOWN, [r'\.md$', r'\.mdml$', r'\.markdown$', r'\.md$', r'\.mkd$']),
    (CSS, [r'\.css$']),
    (JSON, [r'\.json$']),
    (JAVASCRIPT, [r'\.js$']),
    (COFFEESCRIPT, [r'\.coffee$']),
    (ACTIONSCRIPT, [r'\.as$']),
    (VBSCRIPT, [r'\.vbs$']),
    (LUA, [r'\.lua$']),
    (JAVA, [r'\.java$', r'\.jsp$']),
    (C, [r'\.h$', r'\.c$']),
    (CPP, [r'\.cpp$', r'\.hpp$', r'\.c\+\+$', r'\.cc$', r'\.cxx$', r'\.hxx$',
           r'\.hh$', r'\.h\+\+$', r'\.C$', r'\.H$']),
    (OBJECTIVEC, [r'\.m$', r'\.mm$']),
    (VALA, [r'\.vala$', r'\.vapi$']),
    (CSHARP, [r'\.cs$']),
    (D, [r'\.d$', r'\.di$']),
    (SQL, [r'\.sql$']),
    (LISP, [r'\.lisp$', r'\.el$']),
    (CLOJURE, [r'\.clj$']),
    (INI, [r'\.ini$']),
    (APACHE, [r'apache.conf$']),
    (CMAKE, [r'CMakeLists\.txt$', r'\.cmake$', r'\.ctest$']),
    (VHDL, [r'\.vhd$', r'\.vhdl$']),
    (DIFF, [r'\.patch$', r'\.diff$', r'\.rej$', r'\.debdiff$', r'\.dpatch$']),
    (BASH, [r'\.sh$', r'\.[kza]sh$', r'^configure(\.in){0,2}$',
            r'^configure\.ac$', r'\.bash$', r'\.m4$']),
    (TEX, [r'\.tex$', r'\.sty$', r'\.idx$', r'\.ltx$', r'\.latex$']),
    (BRAINFUCK, [r'\.bf$']),
    (HASKELL, [r'\.hs$', r'\.lhs$']),
    (ERLANG, [r'\.erl$']),
    (RUST, [r'\.rs$']),
    (R, [r'\.r$', r'\.R$']),
    (OCAML, [r'\.ml$', r'\.mli$']),
    (SCILAB, [r'\.sci$', r'\.sce$']),
    (MAKEFILE, [r'^(GNUm|m|M)akefile$']),
    ]

# Shebang map:
# from http://git.geany.org/geany/tree/src/filetypes.c?h=1.23#n910
shebangs = dict(
    sh=BASH,
    bash=BASH,
    dash=BASH,
    perl=PERL,
    python=PYTHON,
    php=PHP,
    ruby=RUBY,
    # tcl =	TCL,
    make=MAKEFILE,
    zsh=BASH,
    ksh=BASH,
    csh=BASH,
    ash=BASH,
    dmd=D,
    # wish = TCL,
    )

# if the mime type of the file contains one of the below items,
# the file will be considered as a text file
text_file_mimes = [
    "text",
    "xml",
    "x-empty"
]


def get_filetype(filename, firstline):
    """
    Tries to guess the programming language used in the file.

    It firsts looks at the first line, if it's a shebang:
    #!/usr/bin/env foo

    And if it's not successful it looks at the filename.
    """
    filetype = get_filetype_from_firstline(firstline)
    if filetype is None:
        filetype = get_filetype_from_filename(filename)

    return filetype


def get_filetype_from_firstline(firstline):
    """
    Tries to guess the language with the first line of a file.
    Looks for a shebang, or html/xml/php typical begin tags.
    """
    # we check if it's a shebang:
    if firstline.startswith("#!"):
        # we get the last part:
        interp = firstline.split("/")[-1]
        if interp.startswith("env"):  # shebang #!/usr/bin/env foo
            interp = interp.split()[-1]
        else:  # shebang #!/usr/bin/foo
            # ignore options passed to the interpreter
            interp = interp.split()[0]
        if interp in shebangs.keys():
            return shebangs[interp]
        else:
            return None
    elif (firstline.lower().startswith("<html")
          or firstline.lower().startswith("<!doctype html")):
        return HTML
    elif firstline.lower().startswith("<?xml"):
        return XML
    elif firstline.lower().startswith("<?php"):
        return PHP
    else:
        return None


def get_filetype_from_filename(filename):
    """
    Ties to guess the language with the filename (and the regexes table).
    """
    for language, patternslist in filename_regexes:
        for pattern in patternslist:
            try:
                if re.search(pattern, filename):
                    return language
            except:
                raise Exception("Regex error: " + str(language)
                                + " " + str(pattern))
    return None


def get_highlightjs_language(filename, firstline, lang):
    """
    Returns the highligth.js string corresponding to a language
    (used for syntactic code coloration).
    """
    if lang is not None:
        if lang not in six.itervalues(highlightjs):
            return None
        else:
            return lang

    firstline = firstline.rstrip()
    lang = get_filetype(filename, firstline)
    if lang is None or lang not in highlightjs.keys():
        return None
    else:
        return highlightjs[lang]


def is_text_file(mimetype):
    """
    True if the passed mime corresponds to the mime of a text file,
    False otherwise.
    """
    for text_mime in text_file_mimes:
        if text_mime in mimetype:
            return True
    return False
