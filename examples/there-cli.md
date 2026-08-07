# The `there` command-line interface

PythonHere can be used from Jupyter through the `%there` and `%%there` magics,
or from a terminal through the `there` CLI. Both connect to the same running
PythonHere application. This page covers the PythonHere-specific CLI workflow
and runtime helpers. See the
[Herethere CLI documentation](https://herethere.me/library/there_cli.html) for
the full command reference, connection settings, JSON response fields, and exit
codes.

## Connect to the app

Start PythonHere on the target device, then work from a directory containing a
[`there.env`](https://herethere.me/pythonhere/examples/commands.html#there-env-example)
connection file, or one of its descendants. Check the installed interface and
target readiness:

```console
there --help
there --json ping
```

Use `--config` when the connection file is elsewhere:

```console
there --json --config /path/to/there.env ping
```

Options for the whole invocation, including `--json`, `--config`, `--timeout`,
and `--max-output`, go before the command name.

## Background execution

By default, `run` and `get` execute on the application's main thread. Blocking
or long-running work there can freeze the Kivy UI. Use `--background` to run
such work in a worker thread:

```console
there --json run --background long_task.py
there --json get --background "task_done.wait(30)"
```

The CLI remains attached and waits for the background operation to finish.
Direct Kivy UI access must still run on Kivy's main thread. The `tools_here`
helpers described below marshal their own Kivy operations to that thread.

## Runtime helpers

PythonHere's `tools_here` module provides helpers for inspecting the live Kivy
application and retrieving rendered output:

- `runtime_info(app=None, root=None)` returns compact runtime metadata.
- `snapshot_ui(widget=None, ...)` returns a bounded widget-tree snapshot.
- `save_screenshot(path, widget=None)` saves the window or a widget as PNG.
- `encoded_screenshot(widget=None)` returns a base64-encoded PNG.
- `pin_shortcut(script, label=None)` requests an Android launcher shortcut. Use
  it only when a shortcut is explicitly wanted; upload the script first.

These helpers can be called from either Kivy's main thread or a worker thread.
A worker call is marshalled to Kivy's thread and waits for completion. This
applies only to these helpers; it does not make arbitrary Kivy operations
thread-safe.

### Inspect the running application

`runtime_info` returns a compact summary of the live application, root widget,
Kivy version, platform, and window size:

```console
there --json get "__import__('tools_here').runtime_info(app, root)"
```

`snapshot_ui` returns a bounded, JSON-compatible description of the visible
widget tree:

```console
there --json get "__import__('tools_here').snapshot_ui(root)"
```

Each widget record includes a structural path, class, text where available,
disabled state, geometry, and child count. Snapshot paths describe only that
snapshot; they can change after the widget tree changes and should not be used
as persistent selectors.

The default snapshot is limited to six levels and 200 visited widgets. When a
larger result is needed, raise the soft limits within the helper's hard
ceilings:

```console
there --json get "__import__('tools_here').snapshot_ui(root, max_depth=10, max_widgets=400)"
```

Check the returned `truncated` field before assuming the whole tree was
captured. After mounting or changing widgets, inspect them in a later `there`
request so Kivy has an opportunity to perform layout.

### Customize UI records

Use `widget_record_callback` when the default snapshot does not include an
application-specific property. For anything beyond a short expression, put the
code in a local UTF-8 file instead of building a long shell command.

For example, save this as `inspect_ui.py`:

```python
from tools_here import snapshot_ui


def inspect_widget(widget, record):
    if hasattr(widget, "value"):
        record["value"] = widget.value
    return record


pythonhere_ui_snapshot = snapshot_ui(
    root,
    widget_record_callback=inspect_widget,
)
```

Run it and retrieve the resulting global:

```console
there --json run inspect_ui.py
there --json get "pythonhere_ui_snapshot"
```

### Capture a screenshot

Save a PNG in PythonHere's upload directory, then download it for local visual
inspection:

```console
there --json run --code "from tools_here import save_screenshot; save_screenshot('pythonhere-screen.png', root)"
there --json download pythonhere-screen.png ./pythonhere-screen.png
```

`encoded_screenshot(widget=None)` is also available when a base64-encoded PNG
is needed directly. Saving and downloading a PNG is usually more convenient for
local inspection.
