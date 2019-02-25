from multiprocessing import Process, Queue
from contextlib import contextmanager
import os


__copyright__ = 'Copyright (C) 2019, Nokia'


class _QueueItem(object):
    def __init__(self, ret=None, exception=None):
        self._ret = ret
        self._exception = exception

    def get_return(self):
        if self._exception:
            raise self._exception  # pylint: disable=raising-bad-type
        else:
            return self._ret


class ActivateEnv(object):

    def __init__(self, activate_this):
        self._activate_this = activate_this
        self._env = None

    @property
    def env(self):
        if not self._env:
            self._env = self._get_env_via_process()
        return self._env

    def _get_env_via_process(self):
        q = Queue()
        p = Process(target=self._get_virtualenv_env, args=(q, ))
        p.start()
        return q.get().get_return()

    def _get_virtualenv_env(self, queue):
        with self._return_wrapping(queue):
            self._execfile(self._activate_this,
                           dict(__file__=self._activate_this))

    @staticmethod
    @contextmanager
    def _return_wrapping(queue):
        try:
            yield None
            queue.put(_QueueItem(ret=os.environ.copy()))
        except Exception as e:  # pylint: disable=broad-except
            queue.put(_QueueItem(exception=e))

    @staticmethod
    def _execfile(filename, namespace):
        with open(filename) as f:
            code = compile(f.read(), filename, 'exec')
            exec(code, namespace)  # pylint: disable=exec-used
