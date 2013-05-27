class SourceCodeIterator(object):
    def __init__(self, filename, hl=None):
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
        return (self.file.next(), class_)
