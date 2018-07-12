import os


class DiskUsage:
    def __init__(self, bytes_, path):
        self.bytes_ = bytes_
        self.path = path

    def convert(self):
        '''
        takes a number of bytes as an argument and returns the most suitable human
        readable unit conversion.
        '''
        if bytes_ > 1024**3:
            hr = round(size/1024**3)
            unit = "GB"
        elif bytes_ > 1024**2:
            hr = round(size/1024**2)
            unit = "MB"
        else:
            hr = round(size/1024)
            unit = "KB"

        hr = str(hr)
        result = hr + " " + unit
        return result

    def totalsize(self):
        '''
        Takes a path as an argument and returns the total size in bytes of the file
        or directory. If the path is a directory the size will be calculated
        recursively.
        '''
        total = 0

        if os.path.isdir(self.path):
            for entry in os.scandir(self.path):
                if entry.is_dir(follow_symlinks=False):
                    total += totalsize(entry.self.path)
                else:
                    total += entry.stat(follow_symlinks=False).st_size
        else:
            total += os.path.getsize(self.path)

        return total
