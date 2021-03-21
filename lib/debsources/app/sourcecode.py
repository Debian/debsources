# Copyright (C) 2013  The Debsources developers <qa-debsources@lists.alioth.debian.org>.
# See the AUTHORS file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/AUTHORS
#
# This file is part of Debsources. Debsources is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.  For more information
# see the COPYING file at the top-level directory of this distribution and at
# https://salsa.debian.org/qa/debsources/blob/master/COPYING

from __future__ import absolute_import

from debsources.filetype import get_highlightjs_language


class SourceCodeIterator(object):
    def __init__(self, filepath, hl=None, msg=None, encoding="utf8",
                 lang=None):
        """
        creates a new SourceCodeIterator object

        Arguments:
        filename: the source code file

        Keyword arguments:
        hlbegin: first line whixh will be highlighted
        hlend: last line which will be highlighted
        encoding: the file character encoding
        classes_exts: a tuples list, containing classes to associate with
                      file extensions, eg:
                      [("cpp", ['cpp','hpp']), (...), ...]
        """
        self.filepath = filepath
        self.filename = self.filepath.name
        self.file = open(filepath, encoding=encoding, errors="ignore")
        # we store the firstline (used to determine file language)
        try:
            self.firstline = next(self.file)
        except:  # empty file
            self.firstline = ""

        self.file.seek(0)
        # TODO: proper generator (but 'with' is not available in jinja2)

        self.encoding = encoding
        self.lang = lang
        self.current_line = 0
        self.number_of_lines = None
        self.msgs = msg
        self.hls = set()
        if hl is not None:
            hlranges = hl.split(',')
            for r in hlranges:
                if ':' in r:  # it's a range
                    try:
                        rbegin, rend = r.split(':')
                        for i in range(int(rbegin), int(rend) + 1):
                            self.hls.add(i)
                    except (ValueError, TypeError):
                        pass
                else:  # it's a single line
                    try:
                        self.hls.add(int(r))
                    except:
                        pass

    def __iter__(self):
        return self

    def __next__(self):
        self.current_line += 1
        if self.current_line in self.hls:
            class_ = True
        else:
            class_ = False
        try:
            line = next(self.file)
        except StopIteration:
            # end of file, we close it
            self.file.close()
            raise StopIteration
        return (line, class_)

    def get_number_of_lines(self):
        if self.number_of_lines is not None:
            return self.number_of_lines
        self.number_of_lines = 0
        with open(self.filepath) as sfile:
            for line in sfile:
                self.number_of_lines += 1
        return self.number_of_lines

    def get_file_language(self):
        """
        Returns a class name, usable by highlight.hs, to help it to guess
        the source language.
        """
        return get_highlightjs_language(self.filename,
                                        self.firstline, self.lang)

    def get_msgdict(self):
        """
        returns a dict(position=, title=, message=) generated from
        the string message (position:title:message)
        """
        if self.msgs is None:
            return dict()
        msg_list = []
        for msg in self.msgs:
            msgsplit = msg.split(':')
            msgdict = dict()
            try:
                msgdict['position'] = int(msgsplit[0])
            except ValueError:
                msgdict['position'] = 1
            try:
                msgdict['title'] = msgsplit[1]
            except IndexError:
                msgdict['title'] = ""
            try:
                msgdict['message'] = ":".join(msgsplit[2:])
            except IndexError:
                msgdict['message'] = ""
            msg_list.append(msgdict)
        return msg_list
