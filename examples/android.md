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

## Send SMS


### Request SEND_SMS runtime permission

```python
%there -bl 1 log
```

```python
%%there
from kivy.logger import Logger
from android.permissions import Permission, check_permission, request_permission

def permissions_callback(permissions, grant_results):
    if permissions and all(grant_results):
        Logger.info("Runtime permissions: granted")
    else:
        Logger.error("Runtime permissions: not granted")

permission = Permission.SEND_SMS
if check_permission(permission):
    print(f"{permission} is already granted")
else:
    request_permission(permission, callback=permissions_callback)
```

### Send message with Plyer

```python
%%there
import plyer
plyer.sms.send(recipient=" ", message="Hey!")
```
