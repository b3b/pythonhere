---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.2'
      jupytext_version: 1.7.1
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# Android functions
Android platform features could be used with [PyJNIus](https://github.com/kivy/pyjnius) and [Plyer](https://github.com/kivy/plyer) libraries.

```python
%load_ext pythonhere
%connect-there
```

```python
%%there
from pathlib import Path
from kivy.logger import Logger
from android.permissions import Permission, check_permission, request_permission
import plyer
```

```python
%there -b log
```

## Show notification

```python
%%there
plyer.notification.notify(title='Python', message='Here')
```

## Read accelerometer value

```python
%%there
print(plyer.accelerometer.acceleration)
plyer.accelerometer.enable()
```

```python
%%there --delay 1
print("x: {}, y: {}, z: {}".format(*plyer.accelerometer.acceleration))
```

```python
%%there
plyer.accelerometer.disable()
print(plyer.accelerometer.acceleration)
```

## Write to external storage
Writing to eternal storage is a restricted action.  
If *WRITE_EXTERNAL_STORAGE* permission was not granted to application, access to "/sdcard" will raise *PermissionError*:

```python
%%there
def write_to_sdcard():
    with open("/sdcard/test_python_here.txt", "w") as f:
        f.write("Python everywhere!")
        
write_to_sdcard()
```

```python
%%there shell
touch /sdcard/test_python_here
```

### Request runtime permission

```python
%%there
def permissions_callback(permissions, grant_results):
    if permissions and all(grant_results):
        Logger.info("Runtime permissions: granted %s", permissions)
    else:
        Logger.error("Runtime permissions: not granted, %s", permissions)

def ask_permission(permission):
    if check_permission(permission):
        print(f"{permission} is already granted")
    else:
        request_permission(permission, callback=permissions_callback)
```

```python
%%there
ask_permission(Permission.WRITE_EXTERNAL_STORAGE)
```

The system permission prompt should appear at this point.


### Use external storage


After WRITE_EXTERNAL_STORAGE permission was granted:

```python
%%there
write_to_sdcard()
```

```python
%%there shell
touch /sdcard/test_python_here.txt
cat /sdcard/test_python_here.txt
rm /sdcard/test_python_here.txt
```

###  Application-specific directories
Previous example will not work on Android >= 10,

because of privacy changes: https://developer.android.com/about/versions/10/privacy/changes#scoped-storage

In this case, it is possible to use directories that owned by the application:

```python
%%there
from jnius import autoclass, cast
PythonActivity = autoclass('org.kivy.android.PythonActivity')
Environment = autoclass('android.os.Environment')
context = cast('android.content.Context', PythonActivity.mActivity)
print(context.getExternalFilesDir(None).getAbsolutePath())
print(context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS).getAbsolutePath())
print(context.getExternalFilesDir(Environment.DIRECTORY_PICTURES).getAbsolutePath())
```

## Take picture with a camera
Camera could be displayed and captured with the Kivy [Camera](https://kivy.org/doc/stable/api-kivy.uix.camera.html) widget.

```python
%%there
ask_permission(Permission.CAMERA)
```

```python
%%there kv
Camera:
    play: True
```

```python
%%there
root.export_to_png(filename=str(Path("camera.png").resolve()))
root.play = False
```

```python
%%there  shell
file camera.png
rm camera.png
```
