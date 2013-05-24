class SourceCodeIterator(object):
    def __init__(self, filename):
        self.file = open(filename)
        
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
        return self.file.next()#readline() or raise StopIteration
