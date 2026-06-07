[app]

# title of the application
title = PythonHereDev

# package name
package.name = pythonhere_dev

# package domain (mostly used for android/ios package)
package.domain = me.herethere

# indicate where the source code is living
source.dir = pythonhere
source.include_exts = py,png,kv,rst,rsa,ttf,atlas
p4a.local_recipes = ./recipes

# search the version information into the source code
version.regex = __version__ = "(.*)"
version.filename = %(source.dir)s/version_here.py

orientation = landscape, portrait, landscape-reverse, portrait-reverse
fullscreen = 0

# (str) Presplash of the application
presplash.filename = %(source.dir)s/data/logo/logo-splash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/data/logo/logo-128.png

# requirements of the app
requirements =
             python3==3.14.2,
             hostpython3==3.14.2,
             kivy==2.3.1,
             android,
             pygments==2.20.0,
             # herethere dependencies
             asyncssh==2.23.0,
             python-dotenv==1.2.2,
             herethere==0.2.1,
             # asyncssh dependencies
             cryptography,
             typing_extensions,
             # additional packages
             pyjnius==1.7.0,
             plyer==2.1.0,
             able_recipe,
             midistream==0.3.1,
             # Pillow is a recipe, not a package
             Pillow,
             docutils==0.22.4,
             requests==2.34.2,
             urllib3==2.7.0,
             certifi==2026.4.22,
             chardet==7.4.3,
             idna==3.15,
             # https://github.com/kivy/python-for-android/issues/3098
             filetype==1.2.0,

# android specific
p4a.branch = v2026.05.09             
android.api = 36
android.minapi = 22
android.ndk = 28c
android.accept_sdk_license = True
android.release_artifact = apk

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

android.permissions =
                    WAKE_LOCK,
                    ACCESS_NETWORK_STATE,
                    ACCESS_WIFI_STATE,
                    CHANGE_WIFI_STATE,
                    INTERNET,
                    CAMERA,
                    VIBRATE,
                    WRITE_EXTERNAL_STORAGE,
                    ACCESS_COARSE_LOCATION,
                    ACCESS_FINE_LOCATION,
                    (name=android.permission.BLUETOOTH;maxSdkVersion=30),
                    (name=android.permission.BLUETOOTH_ADMIN;maxSdkVersion=30),
                    BLUETOOTH_SCAN,
                    BLUETOOTH_CONNECT,
                    BLUETOOTH_ADVERTISE,
                    android.permission.MANAGE_EXTERNAL_STORAGE,
                    android.permission.QUERY_ALL_PACKAGES,
                    android.permission.READ_MEDIA_IMAGES,
                    android.permission.PACKAGE_USAGE_STATS,
                    android.permission.POST_NOTIFICATIONS,
                    android.permission.RECORD_AUDIO,

android.wakelock=True
android.manifest.launch_mode = singleTask

[buildozer]
log_level = 2
warn_on_root = 1
