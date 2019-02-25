"""
.. module:: main
    :platform: Unix, Windows
    :synopsis: Tool for running command in virtualenv.
"""
import os
import sys
import subprocess
from contextlib import contextmanager
from collections import namedtuple
from virtualenvrunner.runner import (
    Runner, VerboseRunner, ReadonlyRunner, VerboseReadonlyRunner)
from virtualenvrunner.pythonversionrun import PythonVersionRun
from virtualenvrunner.runnerargparser import (
    RunnerArgParser, CreateArgParser, ReadonlyArgParser)


__copyright__ = 'Copyright (C) 2019, Nokia'


def get_argparser(python_version=None):
    return RunnerArgParser(python_version).parser


def get_createargparser(python_version=None):
    return CreateArgParser(python_version).parser


def get_readonlyargparser(python_version=None):
    return ReadonlyArgParser(python_version).parser


def run(pythonexe=None, python_version=None):
    run_with_runnerargs(lambda: runnerargs(pythonexe, python_version))


def run_install(pythonexe=None,
                python_version=None):
    run_with_runnerargs_and_runnercall(
        lambda: createrunnerargs(pythonexe, python_version),
        createrun_with_runnerargs)


def run_readonly(pythonexe=None,
                 python_version=None):
    run_with_runnerargs(lambda: readonlyrunnerargs(pythonexe, python_version))


def run_with_runnerargs(runnerargsctx):
    run_with_runnerargs_and_runnercall(
        runnerargsctx,
        lambda r: r.runner.run(r.args.commandline))


def run_with_runnerargs_and_runnercall(runnerargsctx, runnercall):
    with _error_handling():
        with runnerargsctx() as r:
            runnercall(r)


def runnerargs(pythonexe=None, python_version=None):
    return runnerargs_from_factories(
        lambda: get_argparser(python_version),
        lambda args: _create_runner(args, pythonexe))


@contextmanager
def runnerargs_from_factories(parser_factory, runner_factory):
    args = parser_factory().parse_args()
    with runner_factory(args) as r:
        yield RunnerArgs(r, args)


def createrun_with_runnerargs(rargs):
    if rargs.args.commandline:
        print("Note: '{args}' have no effect".format(
            args=' '.join(rargs.args.commandline)))


def createrunnerargs(pythonexe=None, python_version=None):
    return runnerargs_from_factories(
        lambda: get_createargparser(python_version),
        lambda args: _create_runner(args, pythonexe))


def readonlyrunnerargs(pythonexe=None, python_version=None):
    return runnerargs_from_factories(
        lambda: get_readonlyargparser(python_version),
        lambda args: _create_readonly_runner(args, pythonexe))


class RunnerArgs(namedtuple('RunnerArgs', ['runner', 'args'])):
    pass


@contextmanager
def _error_handling():
    try:
        yield None
    except Exception as e:  # pylint: disable=broad-except
        print('{cls}: {exc}'.format(
            cls=e.__class__.__name__,
            exc=e))
        sys.exit(1)


def clirun(cmd, env=None):
    if cmd:
        subprocess.check_call(cmd,
                              shell=_is_shell(cmd),
                              env=env)


def _is_shell(cmd):
    return len(cmd) == 1


def _create_runner(args, pythonexe):
    runner = _create_runner_from_args_and_env(_get_runner_cls(args),
                                              args,
                                              pythonexe)
    if args.recreate:
        runner.remove_virtualenv()
    return runner


def _create_runner_from_args_and_env(runnercls, args, pythonexe):
    runner = runnercls(
        virtualenv_dir=_get_arg_env_or_none(args.dir, 'VIRTUALENV_DIR'),
        virtualenv_reqs=_get_arg_env_or_none(
            args.requirements, 'VIRTUALENV_REQS'),
        virtualenv_reqs_upd=_get_arg_env_or_none(
            args.update, 'VIRTUALENV_REQS_UPDATE'),
        virtualenv_pythonexe=pythonexe,
        pip_index_url=_get_arg_env_or_none(args.index, 'PYPI_URL'),
        run=clirun)
    runner.set_save_freeze_path(args.save_freeze_path)
    return runner


def _get_runner_cls(args):
    return VerboseRunner if args.verbose else Runner


def _get_arg_env_or_none(arg, variable):
    return os.environ.get(variable, None) if arg is None else arg


def _create_readonly_runner(args, pythonexe):
    return _create_runner_from_args_and_env(_get_readonly_runner_cls(args),
                                            args,
                                            pythonexe)


def _get_readonly_runner_cls(args):
    return VerboseReadonlyRunner if args.verbose else ReadonlyRunner


PYTHONVERSIONRUN = PythonVersionRun(run)
PYTHONVERSIONRUNINSTALL = PythonVersionRun(run_install)
PYTHONVERSIONRUNREADONLY = PythonVersionRun(run_readonly)
