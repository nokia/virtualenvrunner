from virtualenvrunner.python_versions import get_python_versions
from virtualenvrunner.utils import get_exe_suffix


__copyright__ = 'Copyright (C) 2019, Nokia'


class PythonVersionRun(object):

    def __init__(self, run):
        self._run = run
        self._run_functions = {
            '{run}{major}{minor}'.format(
                major=v.major,
                minor=v.minor,
                run=run.__name__): self._get_run_lambda(v)
            for v in get_python_versions()}

    def _get_run_lambda(self, python_version):
        return lambda: self._run_with_python_version(python_version)

    def _run_with_python_version(self, python_version):
        self._run(pythonexe='python{version}{exe_suffix}'.format(
            version=python_version,
            exe_suffix=get_exe_suffix()),
                python_version=python_version)

    def __getattr__(self, name):
        try:
            return self._run_functions[name]
        except KeyError:
            raise AttributeError('{cls} object has no attribute {name}'.format(  # pylint: disable=raise-missing-from
                cls=self.__class__.__name__,
                name=name))
