Changelog
=========

0.1.10
-----

This is techical release, to check a new releasing workflow.
This release will be deleted after the test.

* Added support for Python 3.10 through 3.14
* Removed support for Python versions older than 3.10
* Updated versions: p4a v2026, Python 3.14, Android API 36  
* Replaced ``nest_asyncio`` usage in tests with ``nest-asyncio2``
* Fixed PythonHere app asyncio lifecycle handling and task shutdown
* Fixed SSH server exception logging
* Avoided duplicate Kivy exception handlers and duplicate KV loading
* Added an Android cryptography recipe workaround for linking failures
* Removed the legacy ``mididriver`` recipe

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
