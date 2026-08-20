---
name: pythonhere
description: "Build, inspect, and debug PythonHere applications by executing Python through the `there` CLI in an already-running Kivy/Python-for-Android process. Use when a task targets a PythonHere device or `there.env` connection and involves live Kivy UI, KV language, Android APIs, Pyjnius, permissions, installed Android packages, media/files, Plyer device features, BLE with able, or MIDI with midistream."
---

# Operate PythonHere with `there`

Treat the target as a live Android/Kivy application. Use the installed `there`
CLI for transport and execution. Consult the `there-cli` skill when the task
needs connection discovery, unfamiliar or version-sensitive syntax, transfers,
timeout or failure diagnosis, or its fuller remote-execution safety guidance.
For routine `ping`, `get`, `logs`, or `run` calls whose invocation is already
established, use the common workflow below without loading `there-cli` solely
because it is the transport.

## Load the relevant runtime rules

The common runtime contract and guardrails are in this file. Consult a reference
only when the task needs its additional detail and that detail is not already
available in the current context. Do not reopen a reference merely because the
request mentions its topic. Read the applicable sections, or the complete file
when the task depends on it broadly or requires its exact current contents.

- Consult [kivy-runtime.md](references/kivy-runtime.md) for nontrivial Kivy
  runtime, lifecycle, threading, state, or UI-construction details beyond the
  guardrails below. A simple property change does not require it.
- Consult [kivy-kv.md](references/kivy-kv.md) for nontrivial KV generation or
  modification details.
- Consult [android-runtime.md](references/android-runtime.md) for Android
  activity, service, context, or lifecycle details.
- Consult [jnius.md](references/jnius.md) for Java/Android API calls through
  Pyjnius.
- Consult [android-permissions.md](references/android-permissions.md) for
  permission checks or requests.
- Consult [android-packages.md](references/android-packages.md) for installed
  applications or package metadata.
- Consult [android-media.md](references/android-media.md) for shared storage,
  MediaStore, images, video, downloads, or galleries.
- Consult [plyer.md](references/plyer.md) for notifications, vibration, TTS,
  recording, camera, file selection, GPS, battery, or sensors.
- Consult [able.md](references/able.md) for Bluetooth Low Energy work.
- Consult [midi.md](references/midi.md) for MIDI or synthesizer work.

Combine references when a feature genuinely needs details from several
concerns; for example, an Android gallery may need permission, MediaStore, and
Pyjnius guidance. Do not load every potentially related reference in advance.

## Use the shared runtime tools

PythonHere provides general helpers in `tools_here`; they are available to
Jupyter commands, agents, and arbitrary code executed in the live runtime.
They complement rather than restrict normal Python:

- `snapshot_ui(widget=None, max_depth=6, max_widgets=200,
  widget_record_callback=None)` returns a bounded, JSON-compatible diagnostic
  snapshot. It reports observable widget paths, classes, text, original text
  length, disabled state, geometry, and child counts. It does not infer KV `id`
  ownership. Lower the soft limits for a narrow inspection; hard ceilings
  prevent more than 48 levels or 500 widgets.
- `runtime_info(app=None, root=None)` returns compact Kivy runtime information.
- `save_screenshot(path="pythonhere-screenshot.png", widget=None)` writes a PNG.
  Relative paths are rooted in the PythonHere upload/SFTP directory.
- `encoded_screenshot(widget=None)` returns the visible content as base64 PNG.
- `pin_shortcut(script, label=None)` requests an Android launcher shortcut.

These helpers may be called on Kivy's main thread or from a worker. Worker calls
are transparently marshaled to Kivy's thread and block that worker until Kivy
finishes the operation, normally on its next frame. Continue to prefer normal
foreground `there get` and `there run` for quick UI operations. Add `--worker`
to `get` or `run` when surrounding slow or blocking work would otherwise block
the UI. The CLI remains attached, waits for completion, and then returns the
value or captured output. Worker execution does not make other Kivy access
thread-safe.

Do not call a worker-marshaled helper while Kivy's main thread is synchronously
waiting for that same worker. Neither side can progress in that cross-thread
wait. A bridge timeout prevents an indefinite wait, but a mutation that already
started may still complete and must not be retried blindly.

Inspect the UI directly with an expression:

```console
there --json get "__import__('tools_here').snapshot_ui(root)"
```

The returned value has this shape:

```json
{
  "widgets": [
    {
      "path": "0/2/1",
      "class": "Button",
      "text": "Expand all",
      "text_length": 10,
      "disabled": false,
      "pos": [16.0, 520.0],
      "size": [180.0, 46.0],
      "child_count": 0
    }
  ],
  "widget_count": 12,
  "truncated": false
}
```

Treat `path` as structural and local to that snapshot. Do not use it as a
persistent widget selector: the path can change whenever the widget tree
changes. When `truncated` is true and the missing portion matters, rerun with
higher soft limits up to `max_depth=48` and `max_widgets=500`. Filter the
returned JSON locally or use arbitrary remote Python for more specific
inspection.

After mounting or changing UI, inspect in a subsequent `there` request or after
one Kivy frame; earlier geometry may still be pre-layout.

For application-specific state, pass `widget_record_callback`. It receives each
live widget and its default record on Kivy's main thread. It may mutate and
return that record, return a replacement dictionary, or return `None` to omit
the record without pruning its children:

```python
def inspect_widget(widget, record):
    if hasattr(widget, "value"):
        record["value"] = widget.value
    return record

snapshot = snapshot_ui(root, widget_record_callback=inspect_widget)
```

For enrichment or redaction, prefer mutating and returning the provided record.
Return a replacement dictionary only when intentionally creating a reduced
custom schema.

The callback may similarly add `str(widget.text)` under a custom `full_text`
field when untruncated text is explicitly needed. Keep the callback fast and
nonblocking: do not sleep, perform I/O, wait for threads, mutate the widget
tree, or start a Kivy event loop. Returned records and all nested values must be
JSON-compatible. A callback exception or invalid result preserves that widget's
default record and adds a compact `inspection_error`; inspection then continues
with later widgets. Omitted records still count toward `max_widgets`.

Inspect compact runtime metadata when diagnosing the target:

```console
there --json get "__import__('tools_here').runtime_info(app, root)"
```

For a screenshot, execute the helper, retrieve the artifact, then inspect the
local image:

```console
there --json run --code "from tools_here import save_screenshot; pythonhere_screenshot = save_screenshot('pythonhere-agent-screenshot.png', root)"
there --json download pythonhere-agent-screenshot.png ./pythonhere-agent-screenshot.png
```

Use `pin_shortcut` only when the user explicitly asks to add a launcher
shortcut. Upload the referenced script first and remember that Android may show
a launcher confirmation:

```console
there --json upload ./demo.py
there --json run --code "from tools_here import pin_shortcut; pin_shortcut('demo.py', 'Demo')"
```

## Workflow

1. Establish the installed CLI interface and target using the `there-cli`
   workflow. Prefer JSON mode and start with `there --json ping` when target
   readiness is not already established.
2. Inspect only the state needed for the task. Prefer small `there --json get`
   expressions for named globals or compact summaries, and `there --json logs`
   for diagnostics. Use `tools_here` inspection or screenshots when structure or
   rendering matters. Remember that `get` evaluates code and is not inherently
   read-only.
3. Design for the live runtime:
   - Assume the Kivy event loop is already running.
   - Assume `app` and the visible `root` container already exist.
   - Preserve useful objects in clearly named globals so later commands can
     inspect, reuse, stop, or release them.
   - Keep callbacks non-blocking and marshal UI changes to the Kivy thread.
4. For more than a short expression, create a local UTF-8 Python file and run it
   with `there --json run FILE`. Prefer a file over fragile shell quoting or a
   long `--code` value. Keep within the installed CLI's input limit. Add
   `--worker` for slow or blocking code that should not occupy Kivy's main
   thread.
5. Make only the requested live-app mutation. Reuse existing state when
   practical and provide cleanup helpers for scheduled events, sensors,
   Bluetooth, MIDI, files, or other held resources.
6. Verify with the narrowest useful observation:
   - inspect a named result/status global with `there --json get`;
   - retrieve relevant recent logs;
   - or inspect the specific widget/state changed.
   Check `ok`, `error`, exit status, and truncation fields before declaring
   success.

## Live-app guardrails

- Do not generate a standalone Kivy application or start/stop an event loop.
- Do not use ADB or local host Android tooling to operate the remote app.
- Do not replace the visible UI unless the user asks. When replacement is
  requested, update the existing `root` container according to the Kivy
  references.
- Do not block the main thread with sleeps, polling loops, network calls, media
  decoding, or long computation.
- Do not rely on callback `print` output. Store callback results/errors in named
  globals and use visible UI status when user feedback is needed.
- Do not blindly retry after an ambiguous mutating failure. Inspect state first
  because the code may already have run.
- Treat permissions, sensors, camera, microphone, location, private files, and
  remote shell execution as capability-sensitive operations. Request or access
  only what the task requires.
- Preserve the running app after expected failures: log the exception, store a
  compact error, and show a useful UI error where appropriate.

## Examples

Inspect the current live root without dumping the widget tree:

```console
there --json get "(type(root).__name__, len(root.children))"
```

Run a prepared UI change:

```console
there --json run /tmp/pythonhere-ui.py
```

Run slow or blocking non-UI work without freezing Kivy, while waiting for its
buffered output:

```console
there --json run --worker /tmp/pythonhere-long-task.py
```

Verify a named status left by that code:

```console
there --json get "pythonhere_feature_status"
```
