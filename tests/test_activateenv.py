# pylint: disable=unused-argument
from collections import namedtuple
import errno
import mock
import pytest
from fixtureresources.fixtures import create_patch
from fixtureresources.mockfile import MockFile
from virtualenvrunner.activateenv import ActivateEnv
from virtualenvrunner.runner import Runner


__copyright__ = 'Copyright (C) 2019, Nokia'

ActivateThis = namedtuple('ActivateThis', ['activate_this', 'runner'])


@pytest.fixture(scope='function')
def mock_activate_this(request):
    runner = Runner()
    activate_this = MockFile('activate_this.py',
                             content='import os\n'
                                     'os.environ["name"] = "value"')
    create_patch(activate_this, request)
    return ActivateThis(activate_this=activate_this, runner=runner)


class RaiseIOErrorOnCounts(object):

    def __init__(self, counts):
        self.counts = counts
        self._count = 0

    def raise_ioerror_enoent(self, *args):
        self._count += 1
        if self._count in self.counts:
            err = IOError('message')
            err.errno = errno.ENOENT
            raise err


@pytest.fixture(scope='function')
def mock_activatethis_enoent(mock_activate_this):
    mock_activate_this.activate_this.set_side_effect(
        RaiseIOErrorOnCounts([1]).raise_ioerror_enoent)
    return mock_activate_this


class MockProcess(object):
    def __init__(self, target, args, *more_args, **kwargs):
        self.target = target
        self.args = args
        self.more_args = more_args
        self.kwargs = kwargs

    def start(self):
        self.target(*self.args)

    def join(self):
        pass


@pytest.fixture(scope='function')
def mock_multiprocessing_process(request):
    """ Because pytest does not support nicely 'multiprocessing.Process'
        Let's run the 'multiprocessing.Process' in the same process.

        .. note:

            Please make sure that the target can be safely executed
            in the same process.
    """

    return create_patch(
        mock.patch('virtualenvrunner.activateenv.Process', new=MockProcess),
        request)


class MockQueue(object):

    def __init__(self):
        self.data = None

    def put(self, data):
        self.data = data

    def get(self):
        return self.data


@pytest.fixture(scope='function')
def mock_multiprocessing_queue(request):
    return create_patch(
        mock.patch('virtualenvrunner.activateenv.Queue', new=MockQueue),
        request)


@pytest.fixture(scope='function')
def monkeypatch_del_name(monkeypatch):
    monkeypatch.delenv('name', raising=False)


def test_activateenv(mock_activate_this,
                     mock_multiprocessing_process,
                     mock_multiprocessing_queue,
                     monkeypatch_del_name):
    assert ActivateEnv(activate_this='activate_this.py').env['name'] == 'value'


def test_ativateenv_raises_ioerror(mock_activatethis_enoent,
                                   mock_multiprocessing_process,
                                   mock_multiprocessing_queue):
    with pytest.raises(IOError) as err:
        ActivateEnv(activate_this='activate_this.py').env
    assert err.value.args[0] == 'message'
