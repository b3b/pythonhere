[app]

# title of the application
title = Python Here

# package name
package.name = pythonhere

# package domain (mostly used for android/ios package)
package.domain = me.herethere

# indicate where the source code is living
source.dir = pythonhere
source.include_exts = py,png,kv,rst,rsa,ttf
#p4a.local_recipes = ../

# search the version information into the source code
version.regex = __version__ = "(.*)"
version.filename = %(source.dir)s/version_here.py

orientation = all
fullscreen = 0

# requirements of the app
requirements = 
             kivy==2.0.0,
             python3, 
             android, 
             pyjnius,              
             plyer, 
             # herethere dependencies
             asyncssh,
             nest_asyncio, 
             python-dotenv,
             herethere,
             # asyncssh dependencies
             cryptography

# android specific

android.api = 28
android.minapi = 22
android.ndk = 19c
             
android.permissions =
                    WAKE_LOCK,
                    INTERNET,
                    CAMERA,
                    VIBRATE,
                    SEND_SMS,
                    CALL_PRIVILEGED,
                    CALL_PHONE,
                    ACCESS_COARSE_LOCATION,
                    ACCESS_FINE_LOCATION,
                    BLUETOOTH,
                    BLUETOOTH_ADMIN


android.wakelock=True

[buildozer]
log_level = 2
warn_on_root = 1
