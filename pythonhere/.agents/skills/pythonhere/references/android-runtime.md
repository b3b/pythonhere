## Android Runtime

The generated code runs inside the Android app's existing Python process.
Assume Python-for-Android/Kivy unless the user says otherwise.

Critical rules:

- Do not use `adb`.
- Do not use `subprocess`, shell commands, or host-side Android tools.
- Do not use legacy SL4A-style Android helper APIs. PythonHere is a
  Kivy/Python-for-Android app, not an SL4A runtime.
- Do not write files unless the user explicitly asks for a file export.
- Prefer Android framework APIs through `jnius` over parsing command output.
- Use the already-running activity or service instead of starting one.
- If the code needs Android context, prefer
  `org.kivy.android.PythonActivity.mActivity`.
- Import `org.kivy.android.PythonService` only inside a fallback block, because
  some apps do not package service support.
- Import every Android class referenced in the code with `autoclass`.
- Import Android nested classes with `$`, not Python attribute access.
- For SDK checks, define `VERSION = autoclass("android.os.Build$VERSION")` and
  use `VERSION.SDK_INT`. Do not use `Build.VERSION.SDK_INT`.
- Convert Java string-like fields to Python strings or `None` before storing
  them.
- Java arrays are Python-indexable in Pyjnius. Use `len(array)` and
  `array[index]`; do not call `.size()` or `.get()` unless the object is a Java
  `List`.
- Do not import `json`, `pathlib.Path`, `pprint`, `os`, `cast`, `contextlib`, or
  other helpers unless the generated code actually uses them.

HTTPS requests:
- Always use certifi, `context = ssl.create_default_context(cafile=certifi.where())`
- Never use urlopen() directly for https:// URLs.
- Never disable SSL verification.
