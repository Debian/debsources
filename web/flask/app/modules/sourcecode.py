# Copyright (C) 2013  Matthieu Caneill <matthieu.caneill@gmail.com>
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


class SourceCodeIterator(object):
    def __init__(self, filename, hl=None, encoding="utf8"):
        """
        creates a new SourceCodeIterator object
        
        Arguments:
        filename: the source code file
        
        Keyword arguments:
        hlbegin: first line whixh will be highlighted
        hlend: last line which will be highlighted
        """
        self.file = open(filename)
        self.encoding = encoding
        self.current_line = 0
        self.hls = set()
        if hl is not None:
            hlranges = hl.split(',')
            for r in hlranges:
                if ':' in r: # it's a range
                    try:
                        rbegin, rend = r.split(':')
                        for i in range(int(rbegin), int(rend) + 1):
                            self.hls.add(i)
                    except ValueError, TypeError:
                        pass
                else: # it's a single line
                    try:
                        self.hls.add(int(r))
                    except:
                        pass
        
    def __iter__(self):
        return self
    
    def next(self):
        self.current_line += 1
        if self.current_line in self.hls:
            class_ = True
        else:
            class_ = False
        return (unicode(self.file.next(), self.encoding), class_)
