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

# Jupyter magic commands

Commands are provided by the *pythonhere* extension

```python
%load_ext pythonhere
```

## %connect-there
**Connect to remote interpreter via SSH**

Command takes single optional argument: location of connection config.<br>
If argument is not provided, values are loaded from the **there.env** file.

Config values could be overridden by environment variables with same names.

```python
import os
os.environ["THERE_PORT"] = "8022"
```

```python
%connect-there there.env
```

### there.env example
```
# PythonHere device IP address
THERE_HOST=127.0.0.1

# Port, as set in PythonHere app Settings section
THERE_PORT=8023

# Username, as set in PythonHere app Settings section
THERE_USERNAME=admin

# Password, as set in PythonHere app Settings section
THERE_PASSWORD=xxx
```


## %there group of commands

```python
%there --help
```

Default action for *%there*, if command is not specified - execute python code.


### there
**Execute python code on the remote side.**<br>

```python
%%there 
import this
```

### kv

```python
%there kv --help
```

If option `--clear-style` is provided,<br> all previous rules, that was loaded with *%%there kv* command,
are unloaded before command execution.

If root widget is defined, it will replace App's current root.



```python
%%there kv
Image:
    source: "../app/data/logo/logo-128.png"
    canvas.before:
        PushMatrix
        Rotate:
            angle: 45
            origin: self.center
    canvas.after:
        PopMatrix
```

### shell

```python
%there shell --help
```

```python
%%there shell
pwd
```

```python
%%there shell
for i in 1 2 3
do
    echo -n "$i"
done
```

<!-- #region hideCode=false -->
Listen to Android system logs in the background and show last two lines of output:
<!-- #endregion -->

```python
%%there -bl 2 shell
logcat
```

### upload

```python
%there upload --help
```

*upload* root directory is application current working directory.

```python
!touch some.ico script.py
!mkdir -p dir1/dir2
```

```python
%there upload some.ico script.py dir1 ../
```

```python
%%there shell
find
```


### pin

```python
%there pin --help
```

```python
%there pin script.py --label "My script"
```

### log

```python
%there log --help
```

```{note}
Since the command blocks and never ends, it is useful to run with --backgroud (-b) option
```

```python
%there -b -l 1 log
```

```python
# wait, to make sure *log* cell connection is established before next cell is executed
import asyncio ; await asyncio.sleep(3)
```

```python
%%there
from kivy.logger import Logger
Logger.info(f"Hello from the main cell")
```

### screeenshot

```python
%there screenshot --help
```

* Wait for half of a second before a command execution,<br>
* make a screenshot,
* display a result constrained to 200px width,
* and save image to a local file:

```python
%there -d 0.5 screenshot -w 200 -o /tmp/screenshot_test.png
```
