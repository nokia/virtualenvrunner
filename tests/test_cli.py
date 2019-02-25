# pylint: disable=unused-argument
import os
from collections import namedtuple
import pytest
from virtualenvrunner.python_versions import get_python_versions


__copyright__ = 'Copyright (C) 2019, Nokia'


def create_patch(patch, request):
    request.addfinalizer(patch.stop)
    return patch.start()


@pytest.fixture(scope='function')
def mock_env(monkeypatch):
    monkeypatch.setenv('VIRTUALENV_DIR', 'virtualenv_dir')
    monkeypatch.setenv('VIRTUALENV_REQS', 'virtualenv_reqs')
    monkeypatch.setenv('VIRTUALENV_REQS_UPDATE', 'TRUE')
    monkeypatch.setenv('PYPI_URL', 'pip_index_url')


@pytest.fixture(scope='function')
def mock_empty_env(monkeypatch):
    monkeypatch.delenv('VIRTUALENV_DIR', raising=False)
    monkeypatch.delenv('VIRTUALENV_REQS', raising=False)
    monkeypatch.delenv('VIRTUALENV_REQS_UPDATE', raising=False)
    monkeypatch.delenv('PYPI_URL', raising=False)


def test_run_in_virtualenv_with_env(script_runner,
                                    mock_env,
                                    mock_subprocess_check_call,
                                    patchermock_real,
                                    tmpdir):
    with tmpdir.as_cwd():
        assert script_runner.run('run_in_virtualenv', 'args').success
        popen_calls = patchermock_real.patch.mock_calls
        virtualenv_call_arg, pip_call_arg = (
            popen_calls[0][1][0], popen_calls[1][1][0])
        assert virtualenv_call_arg.endswith('virtualenv_dir')
        assert '-r virtualenv_reqs' in pip_call_arg
        assert '--upgrade' in pip_call_arg
        assert '-i pip_index_url' in pip_call_arg
        _, check_call_args, _ = mock_subprocess_check_call.mock_calls[0]
        assert check_call_args[0] == ['args']


@pytest.mark.parametrize('args', [['-v', 'args'], ['args']])
def test_create_virtualenv_positional_arguments(script_runner,
                                                mock_subprocess_check_call,
                                                patchermock_real,
                                                tmpdir,
                                                args):
    with tmpdir.as_cwd():
        ret = script_runner.run('create_virtualenv', *args)
        assert "Note: 'args' have no effect" in ret.stdout
        assert ret.success
        assert not mock_subprocess_check_call.called


def get_clis_with_base(base):
    return [base] + [
        '{base}{v.major}.{v.minor}'.format(
            base=base, v=v) for v in get_python_versions()]


def get_base_clis():
    return ['run_in_virtualenv',
            'create_virtualenv',
            'run_in_readonly_virtualenv']


def get_clis():
    return [cli for base in get_base_clis()
            for cli in get_clis_with_base(base)]


def clis():
    return pytest.mark.parametrize('cli', get_clis())


def get_run_tuples():
    return ([(cli, osexe[0], osexe[1]) for osexe in [
        ('win32', 'python.exe'),
        ('linux', 'python')] for cli in get_base_clis()] +
            [t for v in get_python_versions(
                ) for t in get_run_tuples_for_version(v)])


def get_run_tuples_for_version(v):
    return [('{cli}{major}.{minor}'.format(
        major=v.major, minor=v.minor, cli=cli),
             t[0],
             'python{major}.{minor}{suffix}'.format(
                 major=v.major, minor=v.minor, suffix=t[1])) for t in [
                     ('win32', '.exe'),
                     ('linux', '')] for cli in get_base_clis()]


@pytest.mark.parametrize('cli,sys_platform,expected_pythonexe',
                         get_run_tuples())
def test_versioned_cli(monkeypatch,
                       script_runner,
                       patchermock_real,
                       cli,
                       sys_platform,
                       expected_pythonexe,
                       tmpdir):
    with tmpdir.as_cwd():
        monkeypatch.setattr('sys.platform', sys_platform)
        ret = script_runner.run(cli)
        print(ret.stdout, ret.stderr)
        assert ret.success
        _, virtualenv_call_args, _ = patchermock_real.patch.mock_calls[0]
        assert expected_pythonexe + ' ' in virtualenv_call_args[0]


@pytest.mark.parametrize('args', [
    ['--recreate', 'args'],
    ['--update', 'args']])
@pytest.mark.parametrize('cli',
                         get_clis_with_base('run_in_readonly_virtualenv'))
def test_run_in_readonly_env(script_runner,
                             mock_subprocess_check_call,
                             patchermock_real,
                             tmpdir,
                             cli,
                             args):
    with tmpdir.as_cwd():
        ret = script_runner.run('create_virtualenv')
        print(ret.stdout, ret.stderr)
        assert ret.success
        patchermock_real.patch.reset_mock()
        ret = script_runner.run(cli, *args)
        print(ret.stdout, ret.stderr)
        assert ret.success
        assert not patchermock_real.patch.called
        _, check_call_args, _ = mock_subprocess_check_call.mock_calls[0]
        assert check_call_args[0] == ['args']


def get_mock_pip_call(popen_mock):
    return popen_mock.patch.mock_calls[1][1][0]


def get_mock_virtualenv_call(popen_mock):
    return popen_mock.mock_calls[0][1][0]


@clis()
@pytest.mark.parametrize('index_arg_name', ['-i', '--index'])
def test_index_argument(script_runner,
                        patchermock_real,
                        index_arg_name,
                        tmpdir,
                        cli):
    with tmpdir.as_cwd():
        assert script_runner.run(cli,
                                 index_arg_name, 'index',
                                 '-r', 'requirements').success
        assert '-i index' in get_mock_pip_call(patchermock_real)


@clis()
@pytest.mark.parametrize('requirements_arg_name', ['-r', '--requirements'])
def test_requirements_argument(script_runner,
                               patchermock_real,
                               tmpdir,
                               requirements_arg_name,
                               cli):
    with tmpdir.as_cwd():
        assert script_runner.run(cli,
                                 requirements_arg_name, 'requirements').success
        assert '-r requirements' in get_mock_pip_call(patchermock_real)


fileinvenv = os.path.join('.venv', 'filename')


@clis()
def test_recreate_argument(script_runner,
                           patchermock_real,
                           tmpdir,
                           cli):

    with tmpdir.as_cwd():
        script_runner.run('create_virtualenv')
        open(fileinvenv, 'a').close()
        assert script_runner.run(cli, '--recreate').success
        assert os.path.isfile(fileinvenv) == ('readonly' in cli)


@clis()
@pytest.mark.parametrize('dir_arg_name', ['-d', '--dir'])
def test_dir_argument(script_runner,
                      patchermock_real,
                      tmpdir,
                      dir_arg_name,
                      cli):
    with tmpdir.as_cwd():
        assert script_runner.run(cli, dir_arg_name, 'dir').success
        assert get_mock_virtualenv_call(patchermock_real.patch).endswith('dir')


@clis()
@pytest.mark.parametrize('update_arg_name', ['-u', '--update'])
def test_update_argument(script_runner,
                         patchermock_real,
                         tmpdir,
                         update_arg_name,
                         cli):
    with tmpdir.as_cwd():
        assert script_runner.run(cli, '-r', 'requirements',
                                 update_arg_name).success
        for upopt in [' --upgrade ', ' --upgrade-strategy only-if-needed ']:
            assert upopt in get_mock_pip_call(patchermock_real)


@clis()
@pytest.mark.parametrize('verbose_args', [
    ['-v'], ['--verbose'], []])
def test_verbose_argument(script_runner,
                          patchermock_real,
                          tmpdir,
                          verbose_args,
                          cli):
    with tmpdir.as_cwd():
        ret = script_runner.run(cli, '-r', 'requirements', *verbose_args)
        assert ret.success
        assert ('pip install out' in ret.stdout) == bool(verbose_args)


@clis()
def test_save_freeze_path_argument(script_runner,
                                   patchermock_real,
                                   save_freeze,
                                   cli):

    ret = script_runner.run(cli, '-r', 'requirements', *save_freeze.args)
    assert ret.success, (ret.stdout, ret.stderr)
    freeze = read_path(save_freeze.path)
    assert freeze == '\n'.join(patchermock_real.mock.freeze_lines) + '\n'


def read_path(path):
    with open(path) as f:
        return f.read()


class SaveFreeze(namedtuple('SaveFreeze', ['args', 'path'])):
    pass


@pytest.fixture(params=[['-s'], ['--save-freeze-path']])
def save_freeze(tmpdir, request):
    with tmpdir.as_cwd():
        path = os.path.join(tmpdir.dirname, tmpdir.basename, 'savefreeze')
        yield SaveFreeze(args=request.param + [path], path=path)


def _get_versioned_run_scripts_with_expected_help():
    return [(
        '{cli}{major}.{minor}'.format(
            major=v.major,
            minor=v.minor,
            cli=cli),
        'python{major}.{minor}'.format(
            major=v.major,
            minor=v.minor))
            for v in get_python_versions()
            for cli in get_base_clis()]


@pytest.mark.parametrize(
    'versioned_run_script, expected_in_help',
    _get_versioned_run_scripts_with_expected_help())
def test_python_versions_in_help(script_runner,
                                 versioned_run_script,
                                 expected_in_help):
    assert expected_in_help in script_runner.run(
        versioned_run_script, '-h').stdout


EXPECTED_COMMON_ARGS_HELPS = ["Path to 'pip freeze' file"]


@clis()
def test_common_args_help(script_runner, cli):
    h = script_runner.run(cli, '-h')
    for t in EXPECTED_COMMON_ARGS_HELPS:
        assert t in h.stdout, (h.stdout, h.stderr)


class ExpectedException(Exception):
    pass


@clis()
def test_error_handling(script_runner,
                        mock_subprocess_popen_pip_raises_exception,
                        tmpdir,
                        capsys,
                        cli):

    with tmpdir.as_cwd():
        ret = script_runner.run(cli, '-r', 'requirements')
        assert ret.returncode == 1
        assert 'Exception: message' in ret.stdout


@pytest.mark.parametrize('args, expected_call_args, expected_shell', [
    (['args'], ['args'], True),
    (['arg1', 'arg2'], ['arg1', 'arg2'], False),
    (['arg1 arg2'], ['arg1 arg2'], True)])
def test_run_in_virtualenv_commandline(script_runner,
                                       patchermock_real,
                                       mock_subprocess_check_call,
                                       tmpdir,
                                       args,
                                       expected_call_args,
                                       expected_shell):
    with tmpdir.as_cwd():
        assert script_runner.run('run_in_virtualenv', *args).success
        _, args, kwargs = mock_subprocess_check_call.mock_calls[0]
        assert args[0] == expected_call_args
        assert kwargs['shell'] == expected_shell
