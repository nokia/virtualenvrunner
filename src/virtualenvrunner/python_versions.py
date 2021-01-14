__copyright__ = 'Copyright (C) 2021, Nokia'


class PythonVersion:
    def __init__(self, major, minor):
        self.major = str(major)
        self.minor = str(minor) if minor is not None else ''

    def __str__(self):
        if not self.minor:
            return self.major
        return '{}.{}'.format(self.major, self.minor)


def get_python_versions():
    for v in [(2, None), (2, 7), (3, None), (3, 4), (3, 5), (3, 6), (3, 7)]:
        yield PythonVersion(*v)
