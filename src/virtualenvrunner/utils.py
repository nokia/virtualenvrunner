import sys


__copyright__ = 'Copyright (C) 2019, Nokia'


def is_windows():
    return sys.platform == 'win32'


def get_exe_suffix():
    return '.exe' if is_windows() else ''


def get_unicode(s):
    try:
        return s.decode('utf-8')
    except AttributeError:
        return s
