Changelog
=========

0.2.1
-----

* Updated ``herethere`` package to 0.2.1, adding ``%there get`` and
  ``%there download`` commands
* Fixed Android shortcut icon lookup for ``%there pin``
* Fixed ``%there`` reliability issues in notebooks, including event loop
  handling, port reuse after server shutdown, and cleanup behavior
* Improved Docker JupyterLab defaults
* Separated Android package names:
  ``me.herethere.pythonhere`` for releases and
  ``me.herethere.pythonhere_dev`` for source/self-built builds

0.2.0
-----

This is a major maintenance release focused on updating PythonHere for the
current Android and Python runtime stack. It updates the app to Python 3.14,
python-for-android v2026.05.09, and Kivy 2.3.1, and moves Android APK
distribution from Google Play to GitHub Releases.

* Starting with version ``0.2.0``, PythonHere Android APKs are distributed
  through GitHub Releases as the central distribution channel and are signed
  with the PythonHere Android signing certificate
* Added support for Python 3.10 through 3.14
* Removed support for Python versions older than 3.10
* Updated Android APK builds for current Android versions
* Improved app startup and shutdown handling
* Fixed SSH server exception logging
* Fixed duplicate Kivy exception handlers and duplicate KV loading

0.1.5
-----

* Fixed config loss when updating on Android
* Added *pin* command: create script shortcut
* Allow to start server again if exception occur
* UI changes:

  - Fixed UI freeze on server start
  - Added "new settings takes effect after restart" notification

0.1.4
-----

* Added *midistream* package: MIDI support for Android
* Updated *ABLE* package: get list of bonded BLE devices
* Change exception popup style

0.1.3
-----

* First release version
