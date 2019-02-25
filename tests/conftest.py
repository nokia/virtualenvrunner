import os
import io
import subprocess
import shutil
import sys
from collections import namedtuple
import mock
import pytest
from virtualenvrunner.utils import get_unicode


__copyright__ = 'Copyright (C) 2019, Nokia'


class MockResult(namedtuple('MockResult', ['status', 'stdout', 'stderr'])):
    pass


class IoOutBase(object):
    def __init__(self):
        self.out = None
        self.read_file = None
        self.set_out('')

    def add_out(self, out):
        self.set_out(self.out + out)

    def set_out(self, out):
        self.out = out
        self.read_file = self._create_io(out)

    def _create_io(self, s):
        raise NotImplementedError()


class BytesOut(IoOutBase):

    def _create_io(self, s):
        return io.BytesIO(s.encode('utf-8'))


class StringOut(IoOutBase):

    def _create_io(self, s):
        return io.StringIO(get_unicode(s))


class IoOuts(object):
    def __init__(self, out, err):
        self._out = out
        self._err = err
        self._outf = None
        self._errf = None
        self._ioout_factory = None

    def set_ioout_factory(self, ioout_factory):
        self._ioout_factory = ioout_factory

    @property
    def outf(self):
        if self._outf is None:
            self._outf = self._ioout_factory()
        return self._outf

    @property
    def errf(self):
        if self._errf is None:
            self._errf = (self.outf
                          if self._err == subprocess.STDOUT else
                          self._ioout_factory())
        return self._errf

    @property
    def out(self):
        if self._out == subprocess.PIPE:
            return self.outf.read_file
        return self._out

    @property
    def err(self):
        if self._err == subprocess.STDOUT or self._err == subprocess.PIPE:
            return self.out
        return self._err


class FakePopen(object):
    #  pylint: disable=unused-argument
    def __init__(self, cmd, stdout, stderr, shell, env=None):
        self._stdout = stdout
        self._stderr = stderr
        self._ioouts_factory = None
        self._ioouts = None
        self.returncode = 0

    def set_ioouts_factory(self, ioouts_factory):
        self._ioouts_factory = ioouts_factory

    @property
    def ioouts(self):
        if self._ioouts is None:
            self._ioouts = self._ioouts_factory(out=self._stdout,
                                                err=self._stderr)
        return self._ioouts

    @property
    def stdout(self):
        return self.ioouts.out

    @property
    def stderr(self):
        return self.ioouts.err

    def set_returncode(self, returncode):
        self.returncode = returncode

    def communicate(self):
        out = self.ioouts.out

        return ((out, '')
                if self.stdout == self.stderr else
                (out, self.ioouts.err))


class PopenSideeffectBase(object):
    mock_virtualenv_dirname = (
        'mockwinvenv'
        if sys.platform.startswith('win') else
        'mockvenv')

    def __init__(self, popen_factory):
        self._popen_factory = popen_factory
        self.pip_side_effect = None
        self.returncode = 0
        self.freeze_lines = ['reqspec1', 'reqspec2']
        self.freeze_err = 'pip freeze err\n'

    @property
    def freeze_out(self):
        return '{}\n'.format('\n'.join(self.freeze_lines))

    def side_effect(self, *args, **kwargs):
        popen = self._popen_factory(*args, **kwargs)
        popen.set_returncode(self.returncode)
        self._pip_install_sideeffect(popen.ioouts, args[0])
        self._pip_freeze_sideeffect(popen.ioouts, args[0])
        return popen

    def _pip_install_sideeffect(self, ioouts, *args):
        if args[0].startswith('pip install'):
            if self.pip_side_effect is not None:
                self.pip_side_effect()  # pylint: disable=not-callable
            ioouts.outf.add_out('pip install out\n')
            ioouts.errf.add_out('pip install err\n')

    def _pip_freeze_sideeffect(self, ioouts, *args):
        if args[0] == 'pip freeze':
            ioouts.outf.add_out(self.freeze_out)
            ioouts.errf.add_out(self.freeze_err)


class RealVirtualenvPopen(PopenSideeffectBase):
    def side_effect(self, *args, **kwargs):
        if args[0].startswith('virtualenv'):
            shutil.copytree(
                os.path.join(os.path.dirname(__file__),
                             self.mock_virtualenv_dirname),
                args[0].split()[-1])
        return super(RealVirtualenvPopen, self).side_effect(*args, **kwargs)


class MockVirtualenvPopen(PopenSideeffectBase):
    pass


class PatcherMock(namedtuple('PatchMock', ['patch', 'mock'])):
    pass


@pytest.fixture
def mock_subprocess_popen():
    with mock.patch('subprocess.Popen', spec_set=True) as p:
        yield p


@pytest.fixture
def popen_factory(ioouts_factory):
    def fact(cmd, stdout, stderr, shell, env=None):
        popen = FakePopen(cmd, stdout, stderr, shell, env=env)
        popen.set_ioouts_factory(ioouts_factory)
        return popen

    return fact


@pytest.fixture(params=[BytesOut, StringOut])
def ioouts_factory(request):
    def fact(out, err):
        ioouts = IoOuts(out, err)
        ioouts.set_ioout_factory(request.param)
        return ioouts

    return fact


@pytest.fixture
def patchermock_mock(mock_subprocess_popen, popen_factory):
    return create_patchermock(mock_subprocess_popen,
                              MockVirtualenvPopen(popen_factory))


@pytest.fixture
def patchermock_real(mock_subprocess_popen, popen_factory):
    return create_patchermock(mock_subprocess_popen,
                              RealVirtualenvPopen(popen_factory))


def create_patchermock(mock_subprocess_popen, mock_popen):
    mock_subprocess_popen.side_effect = mock_popen.side_effect
    return PatcherMock(mock_subprocess_popen, mock_popen)


def get_pip_side_effect_patch(patchermock, side_effect):
    patchermock.mock.pip_side_effect = side_effect
    return patchermock.patch


@pytest.fixture
def mock_subprocess_popen_pip_raises_ioerror(patchermock_real):
    def raise_ioerror(*args, **kwargs):  # pylint: disable=unused-argument
        raise IOError('message')

    return get_pip_side_effect_patch(patchermock_real, raise_ioerror)


@pytest.fixture
def mock_subprocess_popen_pip_raises_exception(patchermock_real):
    def raise_exception(*args, **kwargs):  # pylint: disable=unused-argument
        raise Exception('message')

    return get_pip_side_effect_patch(patchermock_real, raise_exception)


@pytest.fixture
def mock_subprocess_popen_fail(patchermock_real):
    patchermock_real.mock.returncode = 1
    return patchermock_real.patch


@pytest.fixture
def mock_subprocess_check_call():
    with mock.patch('subprocess.check_call') as p:
        yield p
