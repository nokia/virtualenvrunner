# pylint: disable=unused-argument
from __future__ import print_function
import tempfile
import os
import sys
from collections import namedtuple
import pytest
import mock
from fixtureresources.fixtures import (  # pylint: disable=unused-import
    mock_gettempdir,
    create_patch,
    mock_os_path_isfile)
from fixtureresources.mockfile import MockFile
from virtualenvrunner.runner import (
    Runner, TmpVenvRunner, VerboseRunner, RunnerInstallationFailed)


__copyright__ = 'Copyright (C) 2019, Nokia'


@pytest.fixture
def mock_os_path_isdir(request):
    return create_patch(mock.patch('os.path.isdir'), request)


@pytest.fixture
def mock_tempfile_mkdtemp(request, mock_gettempdir):
    def mock_mkdtemp(suffix='', prefix='tmp', dir=None):
        return os.path.join(
            dir or tempfile.gettempdir(),
            '{prefix}random{suffix}'.format(prefix=prefix,
                                            suffix=suffix))
    return create_patch(
        mock.patch('tempfile.mkdtemp', mock_mkdtemp), request)


@pytest.fixture
def mock_run():
    return mock.Mock(return_value='return_value')


@pytest.fixture
def mock_shutil_rmtree():
    with mock.patch('shutil.rmtree') as p:
        yield p


class MockResult(namedtuple('MockResult', ['status', 'stdout', 'stderr'])):
    pass


@pytest.fixture
def mock_activateenv(request):
    with mock.patch('virtualenvrunner.runner.ActivateEnv') as p:
        p.return_value.env = {'name': 'value'}
        yield p


@pytest.fixture
def mock_os_path_isfile_false():
    with mock.patch('os.path.isfile', return_value=False) as p:
        yield p


@pytest.fixture
def mock_pydistutilscfg(request):
    mfile = MockFile(filename=Runner().pydistutilscfg)
    create_patch(mfile, request)
    return mfile


@pytest.fixture
def mock_requirements_log_file_raises_tmpdir(request, tmpdir):
    with tmpdir.as_cwd():

        mfile = MockFile(filename=Runner().requirements_log_file,
                         content="reguirements install log")

        def exception(*args, **kwargs):
            raise Exception('message')

        mfile.set_side_effect(exception)
        create_patch(mfile, request)
        return tmpdir


def test_init_without_none(mock_run):
    runner = Runner(virtualenv_dir='virtualenv_dir',
                    virtualenv_reqs='virtualenv_reqs',
                    virtualenv_pythonexe='virtualenv_pythonexe',
                    pip_index_url='pip_index_url',
                    run=mock_run)
    assert runner.virtualenv_dir == 'virtualenv_dir'
    assert runner.virtualenv_reqs == 'virtualenv_reqs'
    assert runner.virtualenv_pythonexe == 'virtualenv_pythonexe'
    assert runner.pip_index_url == 'pip_index_url'


def test_init_with_none(mock_gettempdir):
    runner = Runner()
    assert runner._virtualenv_dir is None  # pylint: disable=protected-access
    assert runner.virtualenv_reqs is None
    assert runner.virtualenv_pythonexe == 'python'


def test_tmpvenv_runner(mock_tempfile_mkdtemp,
                        mock_shutil_rmtree,
                        mock_os_path_isfile,
                        mock_subprocess_check_call,
                        mock_activateenv):
    with TmpVenvRunner() as runner:
        runner.run('cmd')

    assert (mock_subprocess_check_call.mock_calls[0] ==
            mock.call('cmd', shell=True, env={'name': 'value'}, stdout=None))
    mock_shutil_rmtree.assert_called_once_with('tmp/venv_random')


def test_tmpvenv_runner_existing_venv(mock_os_path_isfile,
                                      mock_subprocess_check_call,
                                      mock_activateenv,
                                      mock_shutil_rmtree):
    with TmpVenvRunner(virtualenv_dir='d') as runner:
        runner.run('cmd')

    assert (mock_subprocess_check_call.mock_calls[0] ==
            mock.call('cmd', shell=True, env={'name': 'value'}, stdout=None))

    assert not mock_shutil_rmtree.called


def test_runner(mock_os_path_isfile,
                mock_subprocess_check_call,
                mock_activateenv):
    with Runner() as runner:
        runner.run('cmd')

    assert (mock_subprocess_check_call.mock_calls[0] ==
            mock.call('cmd', shell=True, env={'name': 'value'}, stdout=None))


def test_runner_changed_run(mock_tempfile_mkdtemp,
                            mock_shutil_rmtree,
                            mock_run,
                            mock_os_path_isfile,
                            mock_activateenv):
    with Runner(run=mock_run) as runner:
        runner.run('cmd')

    assert (mock_run.mock_calls[0] ==
            mock.call('cmd', env={'name': 'value'}))


def test_tmpvenv_create_environment(mock_tempfile_mkdtemp,
                                    mock_shutil_rmtree,
                                    mock_subprocess_check_call,
                                    patchermock_real,
                                    mock_activateenv,
                                    mock_os_path_isfile_false,
                                    tmpdir):
    with tmpdir.as_cwd():
        with TmpVenvRunner() as runner:
            runner.run('cmd')

    _, args, _ = patchermock_real.patch.mock_calls[0]
    assert args[0].endswith('tmp/venv_random')
    assert (mock_subprocess_check_call.mock_calls[0] ==
            mock.call('cmd', shell=True, env={'name': 'value'}, stdout=None))


def test_create_environment(mock_subprocess_check_call,
                            patchermock_real,
                            mock_activateenv,
                            mock_os_path_isfile_false,
                            tmpdir):
    with tmpdir.as_cwd():
        with Runner() as runner:
            runner.run('cmd')

        _, args, _ = patchermock_real.patch.mock_calls[0]
        assert args[0] == 'virtualenv --no-download -p python {}'.format(
            os.path.join(os.getcwd(), '.venv'))
        assert (mock_subprocess_check_call.mock_calls[0] ==
                mock.call('cmd', shell=True, env={'name': 'value'},
                          stdout=None))


def test_install_requirements(mock_subprocess_check_call,
                              tmpdir,
                              patchermock_real,
                              capsys):
    with tmpdir.as_cwd():
        with Runner(virtualenv_reqs='virtualenv_reqs'):
            print('out')

    _, args, _ = patchermock_real.patch.mock_calls[1]
    assert args[0] == 'pip install -r virtualenv_reqs'
    out, _ = capsys.readouterr()
    assert 'out' in out


@pytest.mark.parametrize('pip_indexes', [
    ['pip_index_url'],
    ['pip_index_url1', 'pip_index_url2']])
def test_setup_pydistutilscfg(patchermock_real,
                              tmpdir,
                              pip_indexes):
    with tmpdir.as_cwd():
        for pip_index in pip_indexes:
            with Runner(pip_index_url=pip_index) as runner:
                with open(runner.pydistutilscfg) as f:
                    assert f.read() == (
                        '[easy_install]\n'
                        'index_url={index}\n'.format(
                            index=pip_indexes[0]))


@pytest.mark.parametrize('repeat_run', [1, 2])
def test_install_requirements_from_index(
        mock_subprocess_check_call,
        patchermock_real,
        tmpdir,
        repeat_run):
    with tmpdir.as_cwd():
        for _ in range(repeat_run):
            with Runner(pip_index_url='pip_index_url',
                        virtualenv_reqs='virtualenv_reqs') as runner:
                runner_log_file = runner.requirements_log_file

    _, args, kwargs = patchermock_real.patch.mock_calls[1]
    assert kwargs['env'] == runner.env
    assert args == ('pip install -r virtualenv_reqs -i pip_index_url',)
    assert kwargs['shell']
    with open(runner_log_file) as f:
        assert f.read() == repeat_run * (
            'pip install out\n'
            'pip install err\n\n'
            '####################\n'
            'pip freeze:\n'
            'reqspec1\n'
            'reqspec2\n'
            'pip freeze err\n'
            '####################\n')


def test_remove_virtualenv(mock_shutil_rmtree,
                           mock_os_path_isfile,
                           mock_subprocess_check_call):
    Runner().remove_virtualenv()
    mock_shutil_rmtree.assert_called_once_with(
        os.path.join(os.getcwd(), '.venv'), ignore_errors=True)


def test_verbose_runner(mock_subprocess_check_call,
                        patchermock_real,
                        tmpdir,
                        capsys):

    with tmpdir.as_cwd():
        with VerboseRunner(pip_index_url='pip_index_url',
                           virtualenv_reqs='virtualenv_reqs'):
            sys.stdout.write('run output')

    out, _ = capsys.readouterr()
    assert 'pip install out\n' in out
    assert 'pip install err\n' in out
    assert 'reqspec1\n' in out
    assert 'pip freeze err\n' in out


def test_requirementslog_ioerror(patchermock_real,
                                 tmpdir,
                                 capsys):
    with tmpdir.as_cwd():
        with Runner(virtualenv_reqs='virtualenv_reqs') as runner:
            log_file = runner.requirements_log_file

        os.remove(log_file)
        os.makedirs(log_file)

        with Runner(virtualenv_reqs='virtualenv_reqs',
                    virtualenv_reqs_upd='True'):
            print('out')

    out, _ = capsys.readouterr()
    assert 'Error in {} file operation'.format(
        log_file) in out
    assert 'out' in out


def test_requirements_pip_raises_ioerror(
        tmpdir,
        mock_subprocess_popen_pip_raises_ioerror,
        capsys):
    with tmpdir.as_cwd():
        with pytest.raises(IOError) as excinfo:
            with Runner(virtualenv_reqs='virtualenv_reqs'):
                assert 0

    assert str(excinfo.value) == 'message'


def test_install_command_fail(tmpdir,
                              mock_subprocess_popen_fail):
    with tmpdir.as_cwd():
        with pytest.raises(RunnerInstallationFailed) as excinfo:
            with Runner(virtualenv_reqs='virtualenv_reqs'):
                assert 0

    assert str(excinfo.value).startswith("Command execution of 'virtualenv")
    assert str(excinfo.value).endswith("' failed with exit status 1")
