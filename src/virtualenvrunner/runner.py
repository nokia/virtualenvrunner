"""
.. module:: runner
    :platform: Unix, Windows
    :synopsis: Runner for commands in virtualenv
"""
from __future__ import print_function
import tempfile
import shutil
import os
import subprocess
from contextlib import contextmanager
from virtualenvrunner.activateenv import ActivateEnv
from virtualenvrunner.utils import is_windows, get_exe_suffix, get_unicode


__copyright__ = 'Copyright (C) 2019, Nokia'


class RunnerInstallationFailed(Exception):
    pass


class Runner(object):
    """ The Runner class is a runner for commands in the virtualenv.

        By default a temporary *virtualenv* is created to $(pwd)/.venv and
        The user defined new or existing *virtualenv* can be used by
        setting path to *virtualenv_dir* which points to the *virtualenv*
        directory.

        No packages are installed by default to the environment. The
        requirements file can be given via *virtualenv_reqs*. It defines the
        path to requirements file which are installed to the *virtualenv*
        during the setup.

        The Python interpreter can be defined by setting the argument
        *virtualenv_pythonexe*. By default 'python' is used.

        URL to PyPI can be altered via *pip_index_url*. The argument
        *pip_index_url* is an URL to PyPI to be used by both pip and
        :mod:`distutils`.

        The command line *run* call can be changed via callable *run* argument.
        The *run* must be a function similar to :func:`subprocess.check_call`
        with *shell=True*. The *run* function has to be able to take at least
        *env* keyword argument.

        An example usage is shown below:

        >>> from virtualenvrunner.runner import Runner
        >>> pip_index_url='https://example.pypi.com/index/+simple'
        >>> with open('requirements.txt', 'w') as f:
        ...     f.write('crl.devutils')
        ...
        >>> with Runner(virtualenv_reqs='requirements.txt',
        ...             pip_index_url=pip_index_url) as runner:
        ...     runner.run('crl -h')
        ...
        Running virtualenv with interpreter ...

"""
    virtualenv_bin = 'Scripts' if is_windows() else 'bin'
    virtualenv_exe = 'virtualenv'

    def __init__(self,
                 virtualenv_dir=None,
                 virtualenv_reqs=None,
                 virtualenv_reqs_upd=None,
                 virtualenv_pythonexe=None,
                 pip_index_url=None,
                 run=None):
        """ Runner class for virtualenv.

        Kwargs:
        """
        self._virtualenv_dir = virtualenv_dir
        self.virtualenv_reqs = virtualenv_reqs
        if virtualenv_reqs_upd and virtualenv_reqs_upd.lower() == "true":
            self.virtualenv_reqs_upd = (" --upgrade"
                                        " --upgrade-strategy only-if-needed ")
        else:
            self.virtualenv_reqs_upd = ""
        self._virtualenv_pythonexe = virtualenv_pythonexe
        self.pip_index_url = pip_index_url
        self._run = run or self.__run
        self._activateenv = None
        self._files = set()
        self._new_virtualenv = False
        self._save_freeze_path = None

    def __enter__(self):
        self._setup_virtualenv()
        return self

    def __exit__(self, *args):
        pass

    def _setup_virtualenv(self):
        """ The extended Runner classes may alter method *_setup_virtualenv*
        for setting the virtualenv in the specific ways. Please note that this
        is not a hook so the original *_setup_virtualenv* must be called in
        order to guarantee the functionality.
        """
        self._create_virtualenv_if_needed()
        self._set_pydistutilscfg_if_needed()
        self._activateenv = ActivateEnv(self.activate_this)
        self._install_requirements_and_freeze_if_needed()

    def set_save_freeze_path(self, save_freeze_path):
        self._save_freeze_path = save_freeze_path

    @property
    def virtualenv_dir(self):
        return self._virtualenv_dir or os.path.join(os.getcwd(), '.venv')

    @property
    def activate_this(self):
        return os.path.join(self.virtualenv_dir,
                            self.virtualenv_bin,
                            'activate_this.py')

    @property
    def pydistutilscfg(self):
        return os.path.join(
            self.virtualenv_dir,
            '{}pydistutils.cfg'.format('' if is_windows() else '.'))

    @property
    def requirements_log_file(self):
        return os.path.join(
            self.virtualenv_dir,
            '{}virtualenvrunner_requirements.log'.format(
                '' if is_windows() else '.'))

    @property
    def env(self):
        """ Property *env* is :data:`os.environ` of
        *virtualenv*.
        """
        return self._activateenv.env

    @property
    def virtualenv_pythonexe(self):
        return self._virtualenv_pythonexe or 'python' + get_exe_suffix()

    def _create_virtualenv_if_needed(self):
        if not os.path.isfile(self.activate_this):
            self._create_virtualenv()

    def _create_virtualenv(self):
        self._run_in_install(
            '{virtualenv_exe} --no-download -p {virtualenv_pythonexe} '
            '{virtualenv_dir}'.format(
                virtualenv_exe=self.virtualenv_exe,
                virtualenv_pythonexe=self.virtualenv_pythonexe,
                virtualenv_dir=self.virtualenv_dir))
        self._new_virtualenv = True

    def _set_pydistutilscfg_if_needed(self):
        if self.pip_index_url and self.virtualenv_is_volatile:
            self._set_pydistutilscfg()

    @property
    def virtualenv_is_volatile(self):
        return self._new_virtualenv or self.virtualenv_reqs

    def _set_pydistutilscfg(self):
        with open(self.pydistutilscfg, 'w') as f:
            f.write('[easy_install]\n'
                    'index_url={}\n'.format(self.pip_index_url))

    @contextmanager
    def _open_requirements_log_file(self):
        with self._open_path_for_write_if_path(self.requirements_log_file):
            yield None

    @contextmanager
    def _open_path_for_write_if_path(self, path, mode='a'):
        if path is None:
            yield None
        else:
            with self._open_path_for_write(path, mode):
                yield None

    @contextmanager
    def _open_path_for_write(self, path, mode):
        f = None
        try:
            with open(path, mode) as f:
                self._files.add(f)
                yield None

        except IOError as file_err:
            print("Error in {} file operation: Error #{} - {}".format(
                path,
                file_err.errno,
                file_err.strerror))
            if f is not None:
                raise
            yield None
        finally:
            if f in self._files:
                self._files.remove(f)

    def _install_requirements_and_freeze_if_needed(self):
        if self.virtualenv_reqs and self.virtualenv_is_volatile:
            self._pip_install()
            self._pip_freeze_with_banner()
        if self._save_freeze_path is not None:
            self._save_pip_freeze_without_err()

    def _pip_install(self):
        with self._open_requirements_log_file():
            self._run_in_install(
                'pip install {req_update}-r {requirements}{index_arg}'.format(
                    requirements=self.virtualenv_reqs,
                    index_arg=(' -i {}'.format(self.pip_index_url)
                               if self.pip_index_url else ''),
                    req_update=self.virtualenv_reqs_upd),
                env=self.env)

    def _pip_freeze_with_banner(self):
        with self._requirements_log_with_banner():
            self._write_line('pip freeze:\n')
            self._run_in_install('pip freeze', env=self.env)

    def _save_pip_freeze_without_err(self):
        with open(os.devnull, 'w') as devnull:
            with self._open_path_for_write_if_path(self._save_freeze_path,
                                                   mode='w'):
                self._run_in_install('pip freeze', stderr=devnull, env=self.env)

    @contextmanager
    def _requirements_log_with_banner(self):
        with self._open_requirements_log_file():
            with self._banner(20):
                yield None

    @contextmanager
    def _banner(self, banner_length):
        try:
            self._write_line('\n{}\n'.format(banner_length * "#"))
            yield None
        finally:
            self._write_line('{}\n'.format(banner_length * "#"))

    def _run_in_install(self, cmd, stderr=subprocess.STDOUT, env=None):
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=stderr,
                                shell=True,
                                env=env)
        for line in self._lines_in_handle(proc.stdout):
            self._write_line(get_unicode(line))

        self._verify_status(cmd, proc)

    @staticmethod
    def _lines_in_handle(handle):
        while True:
            line = handle.readline()
            if line in [b'', '']:
                break
            yield line

    def _write_line(self, line):
        for f in self._files:
            f.write(line)

    @staticmethod
    def _verify_status(cmd, proc):
        proc.communicate()
        if proc.returncode:
            raise RunnerInstallationFailed(
                "Command execution of '{cmd}'"
                " failed with exit status {returncode}".format(
                    cmd=cmd, returncode=proc.returncode))

    @staticmethod
    def __run(cmd, env=None, stdout=None):
        return subprocess.check_call(cmd, shell=True, env=env, stdout=stdout)

    def run(self, *args, **kwargs):
        kwargscopy = kwargs.copy()
        kwargscopy['env'] = self.env
        return self._run(*args, **kwargscopy)

    def remove_virtualenv(self):
        """Removes the virtualenv if it exists."""
        shutil.rmtree(self.virtualenv_dir, ignore_errors=True)


class TmpVenvRunner(Runner):
    """ This virtualenv runner is otherwise the same in functionality than
    :class:`.Runner` but it uses temporaray virtualenv directory. This
    directory is removed in *__exit__*.
    """
    def __enter__(self):
        self._tmp_virtualenv_dir = None
        return super(TmpVenvRunner, self).__enter__()

    def __exit__(self, *args):
        if self._tmp_virtualenv_dir:
            shutil.rmtree(self._tmp_virtualenv_dir)
        super(TmpVenvRunner, self).__exit__(*args)

    @property
    def virtualenv_dir(self):
        return self._virtualenv_dir or self.tmp_virtualenv_dir

    @property
    def tmp_virtualenv_dir(self):
        if not self._tmp_virtualenv_dir:
            self._tmp_virtualenv_dir = tempfile.mkdtemp(prefix='venv_')
        return self._tmp_virtualenv_dir


class VerboseRunner(Runner):
    """This virtualenv runner is otherwise the same in functionality than
    :class:`.Runner` but it prints the requirements installation log and
    *pip freeze*.
    """

    def _write_line(self, line):
        super(VerboseRunner, self)._write_line(line)
        print(line, end='')


class ReadonlyBase(object):

    @property
    def virtualenv_is_volatile(self):
        return self._new_virtualenv


class ReadonlyRunner(ReadonlyBase, Runner):
    pass


class VerboseReadonlyRunner(ReadonlyBase, VerboseRunner):
    pass
