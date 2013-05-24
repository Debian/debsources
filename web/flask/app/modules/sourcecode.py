class SourceCodeIterator(object):
    def __init__(self, filename, hlbegin=None, hlend=None):
        """
        creates a new SourceCodeIterator object
        
        Arguments:
        filename: the source code file
        
        Keyword arguments:
        hlbegin: first line whixh will be highlighted
        hlend: last line which will be highlighted
        """
        self.file = open(filename)
        self.current_line = 0
        if hlbegin is not None:
            self.hlbegin = hlbegin
            if hlend is not None and hlend >= hlbegin:
                self.hlend = hlend
            else:
                self.hlend = hlbegin
        else:
            self.hlbegin, self.hlend = -1, -1
        
    def __iter__(self):
        return self
    
    def next(self):
        #tell = self.file.tell()
        #line = self.file.readline()
        #if tell == self.file.tell():
        #    self.file.close()
        #    raise StopIteration
        #else:
        #    return line
        self.current_line += 1
        if self.hlbegin <= self.current_line <= self.hlend:
            class_ = "highlight"
        else:
            class_ = ""
        return (self.file.next(), class_)#readline() or raise StopIteration
