PythonHere
==========

.. start-badges
.. image:: https://img.shields.io/pypi/status/pythonhere
    :target: https://pypi.python.org/pypi/pythonhere
    :alt: Status
.. image:: https://img.shields.io/pypi/v/pythonhere.svg
    :target: https://pypi.python.org/pypi/pythonhere
    :alt: Latest version on PyPi
.. image:: https://img.shields.io/docker/v/herethere/pythonhere?color=%23FFD43B&label=Docker%20Image
   :target: https://hub.docker.com/r/herethere/pythonhere
   :alt: Docker Image Version (latest by date)
.. image:: https://img.shields.io/pypi/pyversions/pythonhere.svg
    :target: https://pypi.python.org/pypi/pythonhere
    :alt: Supported Python versions
.. image:: https://github.com/b3b/pythonhere/actions/workflows/tests.yml/badge.svg?branch=master
   :target: https://github.com/b3b/pythonhere/actions/workflows/tests.yml?query=branch%3Amaster
   :alt: CI Status          
.. image:: https://codecov.io/github/b3b/pythonhere/coverage.svg?branch=master
    :target: https://codecov.io/github/b3b/pythonhere?branch=master
    :alt: Code coverage Status
.. end-badges

*PythonHere* lets you run Python code from a local `Jupyter <https://jupyter.org/>`_
notebook inside a remote `Kivy <https://kivy.org>`_ app.

PythonHere has two parts:

* *Here* is the remote/server side. It runs a Python environment with a Kivy GUI,
  for example on Android, Raspberry Pi, or another machine.
* *%there* is the local/client side. It is a Jupyter magic command for running
  code interactively in the remote PythonHere environment.

This makes PythonHere useful as a live Python/Kivy playground, and as a way to
inspect or control a Python app running remotely.

Project documentation: https://herethere.me/pythonhere

.. image:: https://raw.githubusercontent.com/b3b/pythonhere/master/docs/description.png
  :alt: Project description


Install the Android app
-----------------------

Ready-to-use *PythonHere* APKs are available from the `GitHub Releases <https://github.com/b3b/pythonhere/releases>`_ page.

For APK provenance and signing checks, see `Android APK verification <https://github.com/b3b/pythonhere/blob/master/docs/android-apk-verification.rst>`_.
For a list of Python packages included in the Android build, see `buildozer.spec <https://github.com/b3b/pythonhere/blob/master/buildozer.spec>`_.

Start a local Jupyter environment with Docker
---------------------------------------------

The Docker image is based on `Jupyter Docker Stacks <https://jupyter-docker-stacks.readthedocs.io/en/latest/>`_
and includes *PythonHere* with usage examples.

Example command to start the Docker container::

    docker run \
           --rm \
           -p 8888:8888 \
           --user root \
           -e CHOWN_EXTRA=/home/jovyan/work \
           -e CHOWN_EXTRA_OPTS='-R' \
           -v "$(pwd)/work":/home/jovyan/work \
           herethere/pythonhere:latest

The command exposes the Jupyter server on host port ``8888``. Jupyter logs are
printed in the terminal and include a URL such as
``http://127.0.0.1:8888/?token=...``. Open this URL in a browser to use the
local Jupyter environment.

Files in ``/home/jovyan/work`` inside the container are stored in the local
``work`` directory.


Run a local Jupyter environment without Docker
----------------------------------------------

Commands to run locally::

   pip install pythonhere jupyter
   jupyter notebook


Build Android app
-----------------

To build with `Buildozer <https://github.com/kivy/buildozer>`_, run in the source directory::


  buildozer android debug


Related resources
-----------------

* `Kivy Remote Shell <https://github.com/kivy/kivy-remote-shell>`_ : Remote SSH+Python interactive shell application
* `herethere <https://github.com/b3b/herethere>`_ : Library for interactive code execution, based on AsyncSSH
* `AsyncSSH <https://github.com/ronf/asyncssh>`_ : Asynchronous SSH for Python
