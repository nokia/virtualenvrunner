import argparse


__copyright__ = 'Copyright (C) 2019, Nokia'


class RunnerArgParser(object):

    cmdline_help = 'Optional command line to be executed in virtualenv'
    update_help = ('Boolean value (TRUE or FALSE). '
                   'Overrides VIRTUALENV_REQS_UPDATE environmental variable.')
    recreate_help = 'Force recreation of virtual environments'

    def __init__(self, python_version=None):
        self._python_version = python_version
        self.parser = None
        self._initialize_parser()

    @property
    def description(self):
        return 'Runner for {python} virtualenv.'.format(
            python=self._python)

    def _initialize_parser(self):
        self._create_parser_with_description()
        self._add_optional_arguments()
        self._add_commandline()

    def _add_optional_arguments(self):
        self._add_arguments_with_values()
        self._add_flag_arguments()

    def _create_parser_with_description(self):
        self.parser = argparse.ArgumentParser(
            description=self.description)

    @property
    def _python(self):
        return ('python'
                if self._python_version is None else
                'python{major}.{minor}'.format(
                    major=self._python_version.major,
                    minor=self._python_version.minor))

    def _add_arguments_with_values(self):
        self.parser.add_argument(
            '--index', '-i', dest='index',
            help=('URL to PyPI to be used by both pip and distutils. '
                  'Overrides PYPI_URL environmental variable.'),
            default=None)
        self.parser.add_argument(
            '--requirements', '-r', dest='requirements',
            help=('Path to the requirements file. '
                  'Overrides VIRTUALENV_REQS environmental variable.'),
            default=None)
        self.parser.add_argument(
            '--dir', '-d', dest='dir',
            help=('Path to the virtualenv. '
                  'Overrides VIRTUALENV_DIR environmental variable.'),
            default=None)
        self.parser.add_argument(
            '--save-freeze-path', '-s', dest='save_freeze_path',
            help="Path to 'pip freeze' file",
            default=None)

    def _add_flag_arguments(self):
        self.parser.add_argument(
            '--update', '-u', dest='update',
            help=self.update_help,
            action='store_const',
            const='true',
            default=None)
        self.parser.add_argument(
            '--recreate', dest='recreate',
            help=self.recreate_help,
            action='store_true',
            default=False)
        self.parser.add_argument(
            '--verbose', '-v', dest='verbose',
            help='Verbose pip install and freeze',
            action='store_true',
            default=False)

    def _add_commandline(self):
        self.parser.add_argument(
            'commandline', nargs=argparse.REMAINDER,
            help=self.cmdline_help)


class CreateArgParser(RunnerArgParser):

    @property
    def cmdline_help(self):
        return 'Optional command line without effect'

    @property
    def description(self):
        return 'Creates {python} virtualenv.'.format(
            python=self._python)


class ReadonlyArgParser(RunnerArgParser):

    @property
    def update_help(self):
        return 'No effect'

    @property
    def recreate_help(self):
        return 'No effect'
