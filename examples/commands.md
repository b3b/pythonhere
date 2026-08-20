---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.3
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Jupyter magic commands

Commands are provided by the *pythonhere* extension

```{code-cell}
%load_ext pythonhere
```

## %connect-there
**Connect to remote interpreter via SSH**

Command takes single optional argument: location of connection config.<br>
If argument is not provided, values are loaded from the **there.env** file.

Config values could be overridden by environment variables with same names.

```{code-cell}
import os
os.environ["THERE_PORT"] = "8022"
```

```{code-cell}
%connect-there there.env
```

### there.env example
```
# PythonHere device IP address
THERE_HOST=127.0.0.1

# Port, as set in PythonHere app Settings section
THERE_PORT=8022

# Username, as set in PythonHere app Settings section
THERE_USERNAME=here

# Password, as set in PythonHere app Settings section
THERE_PASSWORD=xxx
```

+++

## %there group of commands

```{code-cell}
%there --help
```

Default action for *%there*, if command is not specified - execute python code.

+++

### there
**Execute python code on the remote side.**<br>

```{code-cell} python
:tags: ["hide-output"]
%%there 
import this
```

Python code normally runs on the PythonHere application's main thread. For a
slow or blocking operation, use `--worker` so the UI stays responsive. The cell
waits for completion and then displays the buffered output:

```{code-cell} python
:tags: ["skip-execution"]
%%there --worker
import time


def perform_expensive_work():
    """Simulate a blocking operation."""
    time.sleep(1)
    print("Work complete")


perform_expensive_work()
```

Use `--background` instead when the notebook cell should return immediately
while the code continues on a remote worker thread.

### get

Evaluate a Python expression on the remote PythonHere side and return the value to the local notebook.

```{code-cell}
%there get --help
```

```{code-cell}
%%there
device_status = {
    "root_class": root.__class__.__name__ if "root" in globals() else None,
    "child_count": len(root.children) if "root" in globals() else None,
}
```

```{code-cell}
status = %there get device_status
status
```

The expression is evaluated remotely, so it can also inspect live objects:

```{code-cell}
root_size = %there get tuple(root.size)
root_size
```

Use `%there get` for small and inspectable values. For large text, binary data,
images, CSV files, or directories, write a remote file and use `%there download`.

### kv

```{code-cell}
%there kv --help
```

If option `--clear-style` is provided,<br> all previous rules, that was loaded with *%%there kv* command,
are unloaded before command execution.

If root widget is defined, it will replace App's current root.


```{code-cell}
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

```{code-cell}
%there shell --help
```

```{code-cell}
%%there shell
pwd
```

```{code-cell}
%%there shell
for i in 1 2 3
do
    echo -n "$i"
done
```

+++ {"hideCode": false}

Listen to Android system logs in the background and show last two lines of output:

```{code-cell}
%%there -bl 2 shell
logcat
```

### upload

```{code-cell}
%there upload --help
```

*upload* root directory is application current working directory.

```{code-cell}
%%bash
touch some.ico script.py
mkdir -p dir1/dir2
```

```{code-cell}
%there upload some.ico script.py dir1 ../
```

```{code-cell} python
%%there shell
find
```

### download

```{code-cell}
%there download --help
```

Files are downloaded from the same remote SFTP root used by `%there upload`.

With one remote path, the destination is the current local directory:

```{code-cell}
%there download some.ico
```

Provide a local destination path explicitly:

```{code-cell}
%there download some.ico ./downloaded-some.ico
```

Directories use the same command:

```{code-cell}
%there download dir1 ./downloaded-dir1
```

For generated data that is too large for `%there get`, save it remotely first:

```{code-cell}
%%there
import csv

rows = [
    {"name": "root_class", "value": root.__class__.__name__},
    {"name": "child_count", "value": len(root.children)},
]

with open("pythonhere-report.csv", "w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=["name", "value"])
    writer.writeheader()
    writer.writerows(rows)
```

```{code-cell}
%there download pythonhere-report.csv ./pythonhere-report.csv
```

### pin

```{code-cell}
%there pin --help
```

```{code-cell}
%there pin script.py --label "My script"
```

### log

```{code-cell}
%there log --help
```

```{note}
Since the command blocks and never ends, it is useful to run with --background (-b) option
```

Listen to Python logs in the background and show the last line of output:

```{code-cell}
%there -b -l 1 log
```

```{code-cell}
%%there --delay 4
from kivy.logger import Logger
Logger.info("Example: Hey, Logger!")
```

### screenshot

```{code-cell}
%there screenshot --help
```

* Wait for half of a second before a command execution,<br>
* make a screenshot,
* display a result constrained to 200px width,
* and save image to a local file:

```{code-cell}
%there -d 0.5 screenshot -w 200 -o /tmp/screenshot_test.png
```

## `%%there ai`

Generate a reviewable `%%there` Python cell from a plain-language request.
The generated cell is inserted locally below the prompt cell. Review or edit it
before running it on the connected PythonHere device.

```{code-cell}
%there ai --help
```

```{code-cell}
:tags: ["remove-output"]
%%there ai
Show Python version, Kivy platform, current working directory,
and root widget class.
```

Add an optional prompt section for one request:

```{code-cell}
:tags: ["remove-output"]
%%there ai --prompts midi
Build a small MIDI note test UI with play, stop, and status controls.
```

Generate a replacement for the last executed Python `%%there` cell:

```{code-cell}
:tags: ["remove-output"]
%%there ai --fix
Button was not imported.
```
