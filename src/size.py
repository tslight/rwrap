import os

# takes a number of bytes as an argument and returns the most suitable human
# readable unit conversion.
def convert(size):
    if size > 1024**3:
        hr = round(size/1024**3)
        unit = "GB"
    elif size > 1024**2:
        hr = round(size/1024**2)
        unit = "MB"
    else:
        hr = round(size/1024)
        unit = "KB"

    hr = str(hr)
    result = hr + " " + unit
    return result


# takes a path as an argument and returns the total size in bytes of the file or
# directory. If the path is a directory the size will be calculated recursively.
def totalsize(path):
    total = 0

    if os.path.isdir(path):
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                total += totalsize(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
    else:
        total += os.path.getsize(path)

    return total
