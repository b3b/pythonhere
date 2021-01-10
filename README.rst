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
.. image:: https://github.com/b3b/pythonhere/workflows/ci/badge.svg?branch=master
     :target: https://github.com/b3b/pythonhere/actions?workflow=CI
     :alt: CI Status
.. image:: https://codecov.io/github/b3b/pythonhere/coverage.svg?branch=master
    :target: https://codecov.io/github/b3b/pythonhere?branch=master
    :alt: Code coverage Status
.. end-badges

*Here* is the `Kivy <https://kivy.org>`_ based app to run Python code from the `Jupyter <https://jupyter.org/>`_ magic %there.

- *Here* is a server part with the GUI interface. It could be Android, Raspberry Pi, some other remote device that being debugged.
- And *%there* is a client - Jupyter magic command to run code interactively on remote device.

This app could serve as a Python Kivy playground, for dynamic code execution from the PC.

Project documentation: https://herethere.me

.. image:: https://raw.githubusercontent.com/b3b/pythonhere/master/docs/description.png
  :alt: Project description


Install on Android
------------------

App is available on `Google Play <https://play.google.com/store/apps/details?id=me.herethere.pythonhere>`_.

Ready-to-use *PythonHere* APKs are available in the `Releases <https://github.com/b3b/pythonhere/releases>`_ section.

For a list of installed Python packages, see: `buildozer.spec <./buildozer.spec>`_.


Quick Start with Docker
-----------------------

Docker image is based on `Jupyter Docker Stacks <https://jupyter-docker-stacks.readthedocs.io/en/latest/>`_, and includes installed *PythonHere* with usage examples.

Example command to start the Docker container::

    docker run \
           --rm \
           -p 8888:8888 \
           -v "$(pwd)/work":/home/jovyan/work \
           herethere/pythonhere:latest


Command will expose the Jupyter Notebook server on host port 8888. Jupyter logs appear in the terminal and include an URL to the notebook server: http://127.0.0.1:8888/?token=... . Visiting this URL in a browser loads the Jupyter Notebook dashboard page.

Files from the directory **work** inside container, will be available in the host directory with the same name: **work**.


Run with Docker Compose
-----------------------

Commands to run with Docker Compose, in the source directory:::

  cp docker-compose.yml.tmpl docker-compose.yml
  docker-compose up


Run locally
-----------

Commands to run locally::

   pip install pythonhere
   jupyter notebook start


Build Android app
-----------------

To build with `Buildozer <https://github.com/kivy/buildozer>`_, run in the source directory::


  buildozer android debug



Related resources
-----------------

* `Kivy Remote Shell <https://github.com/kivy/kivy-remote-shell>`_ : Remote SSH+Python interactive shell application
* `herethere <https://github.com/b3b/herethere>`_ : Library for interactive code execution, based on AsyncSSH
* `AsyncSSH <https://github.com/ronf/asyncssh>`_ : Asynchronous SSH for Python
* `Buildozer action <https://github.com/ArtemSBulgakov/buildozer-action>`_ : GitHub action that is used to build Android APK with Buildozer
