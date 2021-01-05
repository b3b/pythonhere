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
from kivy.logger import Logger
from android.permissions import Permission, check_permission, request_permission
import plyer
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
%there -bl 1 log
```

```python
%%there

def permissions_callback(permissions, grant_results):
    if permissions and all(grant_results):
        Logger.info("Runtime permissions: granted")
    else:
        Logger.error("Runtime permissions: not granted")

permission = Permission.WRITE_EXTERNAL_STORAGE
if check_permission(permission):
    print(f"{permission} is already granted")
else:
    request_permission(permission, callback=permissions_callback)
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
