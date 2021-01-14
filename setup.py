
import os
import sys
import imp
from collections import namedtuple
from setuptools import setup, find_packages


__copyright__ = 'Copyright (C) 2019, Nokia'

VERSIONFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'src', 'virtualenvrunner', '_version.py')


def import_module(name, path):
    if sys.version_info.major == 2:
        import imp
        return imp.load_source(name, path)

    import importlib
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_version():
    return import_module('_version', VERSIONFILE).get_version()


python_versions = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'src', 'virtualenvrunner', 'python_versions.py')


def get_python_versions():
    return imp.load_source(
        'python_versions', python_versions).get_python_versions()


class CliFunction(namedtuple('CliFunction', ['cli', 'function'])):
    pass


def get_clifunctions():
    return [
        CliFunction('run_in_virtualenv', 'run'),
        CliFunction('create_virtualenv', 'run_install'),
        CliFunction('run_in_readonly_virtualenv', 'run_readonly')]


def get_versionedclifunctions():
    return  [
        CliFunction('run_in_virtualenv', 'PYTHONVERSIONRUN.run'),
        CliFunction('create_virtualenv',
                    'PYTHONVERSIONRUNINSTALL.run_install'),
        CliFunction('run_in_readonly_virtualenv',
                    'PYTHONVERSIONRUNREADONLY.run_readonly')]


def get_console_scripts():
    return (
        ['{clif.cli} = virtualenvrunner.cli:{clif.function}'.format(
            clif=clif) for clif in get_clifunctions()] +
        [('{clif.cli}{version} = '
          'virtualenvrunner.cli:{clif.function}{major}{minor}'.format(
             version=v, major=v.major, minor=v.minor, clif=clif))
         for v in get_python_versions()
         for clif in get_versionedclifunctions()])


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


setup(
    name='virtualenvrunner',
    version=get_version(),
    author='Petri Huovinen',
    author_email='petri.huovinen@nokia.com',
    description='Runner for shell commands in virtualenv',
    install_requires=['virtualenv>=15.1.0'],
    long_description=read('README.rst'),
    license='BSD 3-Clause',
    classifiers=['Intended Audience :: Developers',
                 'License :: OSI Approved :: BSD License',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Topic :: Software Development'],
    keywords='virtualenv',
    url='https://github.com/nokia/virtualenvrunner',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    entry_points={'console_scripts': get_console_scripts()}
)
