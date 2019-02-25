from collections import namedtuple


__copyright__ = 'Copyright (C) 2019, Nokia'


class PythonVersion(namedtuple('PythonVersion', ['major', 'minor'])):
    pass


def get_python_versions():
    for v in [(2, 7), (3, 4), (3, 5), (3, 6)]:
        yield PythonVersion(*v)
