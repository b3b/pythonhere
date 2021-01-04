[app]

# title of the application
title = PythonHere

# package name
package.name = pythonhere

# package domain (mostly used for android/ios package)
package.domain = me.herethere

# indicate where the source code is living
source.dir = pythonhere
source.include_exts = py,png,kv,rst,rsa,ttf,atlas
#p4a.local_recipes = ../

# search the version information into the source code
version.regex = __version__ = "(.*)"
version.filename = %(source.dir)s/version_here.py

orientation = all
fullscreen = 0

# (str) Presplash of the application
presplash.filename = %(source.dir)s/data/logo/logo-splash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/data/logo/logo-128.png

# requirements of the app
requirements = 
             kivy==2.0.0,
             python3,
             android,
             pygments==2.7.3,
             # herethere dependencies
             asyncssh==2.4.2,
             nest-asyncio==1.4.3,
             python-dotenv==0.15.0,
             herethere,
             # asyncssh dependencies
             cryptography,
             # additional packages
             pyjnius==1.3.0,
             plyer==2.0.0,
             able_recipe,
             Pillow,
             numpy,
             requests==2.24.0,
             urllib3==1.25.9,
             certifi==2019.6.16,
             chardet==3.0.4,
             idna==2.8,


# android specific

android.api = 29
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
