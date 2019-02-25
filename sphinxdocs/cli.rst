.. Copyright (C) 2019, Nokia

Command line interface
----------------------

.. this requires sphinx-argparse extension package

.. _run_in_virtualenv:

run_in_virtualenv
^^^^^^^^^^^^^^^^^

.. argparse::
   :ref: virtualenvrunner.cli.get_argparser
   :prog: run_in_virtualenv

    The tool *run_in_virtualenv* is a command line runner for commands in
    virtualenv.

    The default interpreter in the command line is *python*.  The interpreters
    *python2.7* and *python3.x* can be forced by using *run_in_virtualenv2.7*
    and *run_in_virtualenv3.x* respectively.

    .. note::

        Python interpreters have to be installed into the system prior
        running of the tool. The tool itself does not check whether or
        not the interpreter is installed.

*run_in_virtualenv* tool can be steered by the following environmental
variables:

+-------------------------+-------------------------------------------+
| Variable                |  Description                              |
+=========================+===========================================+
| VIRTUALENV_DIR          | Path to the virtualenv directory.         |
|                         | If not defined, then temporary virtualenv |
|                         | is used. Virtualenv is created only if    |
|                         | it does not exist.                        |
+-------------------------+-------------------------------------------+
| VIRTUALENV_REQS         | Path to the requirements file.            |
|                         | If not defined, no requirements are       |
|                         | are installed.                            |
+-------------------------+-------------------------------------------+
| VIRTUALENV_REQS_UPDATE  | Boolean value (TRUE or FALSE).            |
|                         | If this variable TRUE the requirements    |
|                         | will install with the update parameter.   |
|                         | If version is not given then the package  |
|                         | will update to the latest version.        |
+-------------------------+-------------------------------------------+
| PYPI_URL                | URL to PyPI to be used by both pip        |
|                         | and :mod:`distutils`.                     |
+-------------------------+-------------------------------------------+

create_virtualenv
^^^^^^^^^^^^^^^^^

.. argparse::
   :ref: virtualenvrunner.cli.get_createargparser
   :prog: create_virtualenv

    Create virtualenv without running commands but otherwise functionality is
    the same as :ref:`run_in_virtualenv`. Even command line can be given to
    *create_virtualenv* but it has no effect.

run_in_readonly_virtualenv
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. argparse::
   :ref: virtualenvrunner.cli.get_readonlyargparser
   :prog: run_in_readonly_virtualenv

    Run commands the same way than :ref:`run_in_virtualenv` but neither update
    nore recreate the environment if it exists already.
