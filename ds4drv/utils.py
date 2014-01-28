import sys

def zero_copy_slice(buf, start = None, end = None):
    # No need for an extra copy on Python 3.3+
    if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
        buf = memoryview(buf)

    return buf[start:end]
