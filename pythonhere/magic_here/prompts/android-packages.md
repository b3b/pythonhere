## Android Package Inventory

Use this addon when the user asks to list, inspect, filter, summarize, or export
installed Android apps, packages, APK files, package labels, versions, system-app
status, or requested permissions for installed packages.

PackageManager rules:

- Use `org.kivy.android.PythonActivity.mActivity`.
- Import `org.kivy.android.PythonService` inside the fallback block, not before
  it is needed, because some apps do not package service support.
- Get a `PackageManager` from the Android context.
- Use `PackageManager.getInstalledPackages(...)` with `GET_PERMISSIONS`.
- In Pyjnius, import Android nested classes with `$`, not Python attribute
  access. For SDK checks, define
  `VERSION = autoclass("android.os.Build$VERSION")` and use
  `VERSION.SDK_INT`. Do not use `Build.VERSION.SDK_INT`.
- On Android API 33+, call `PackageInfoFlags.of(...)`.
- On older Android versions, pass integer flags directly.
- In Pyjnius, the Android API 33 flags class must be imported as:
  `PackageInfoFlags = autoclass("android.content.pm.PackageManager$PackageInfoFlags")`.
  Then call `PackageInfoFlags.of(flags)`. Do not call
  `PackageManager.PackageInfoFlags.of(...)`.
- Use `android.content.pm.ApplicationInfo.FLAG_SYSTEM` and
  `FLAG_UPDATED_SYSTEM_APP` for system app detection.
- Do not use `android.content.pm.ActivityInfo` for installed application flags.
- Use `ApplicationInfo.sourceDir` and `splitSourceDirs` with `java.io.File` for
  APK file sizes. Report `None` when a path is unavailable.
- Store APK size details separately, for example `base_apk_size_bytes`,
  `split_apk_sizes_bytes`, and `total_apk_size_bytes`.
- Use `PackageInfo.requestedPermissions` plus
  `PackageInfo.requestedPermissionsFlags`.
- A requested permission is granted when the matching flag has
  `PackageInfo.REQUESTED_PERMISSION_GRANTED` set.
- Do not use `PackageManager.PERMISSION_GRANTED` or
  `ActivityInfo.REQUESTED_PERMISSION_GRANTED` for requested permission flags.
- Import every Android class referenced in the code with `autoclass`.
  If code uses `PackageInfo.REQUESTED_PERMISSION_GRANTED`, it must first define
  `PackageInfo = autoclass("android.content.pm.PackageInfo")`.
- `requestedPermissions`, `requestedPermissionsFlags`, and `splitSourceDirs` are
  Java arrays. In Pyjnius, handle them with `len(array)` and `array[index]`;
  do not call `.size()` or `.get()` on them.
- Keep per-app permission records as dictionaries with at least `name` and
  `granted`.
- Convert Java string-like fields such as package name, label, and version name
  to Python strings or `None` before storing them.
- Keep preview output simple. If you compute `perms_granted`, print
  `perms_granted`; do not reference a different variable name.
- Do not import `json`, `pathlib.Path`, or `pprint` unless the user explicitly
  asks to export or pretty-print data.
- Do not import `os` unless the user explicitly asks for filesystem or
  environment inspection.
- Do not import `cast`, `contextlib`, or other helpers unless the generated code
  actually uses them.

Android 11+ package visibility:

- On Android 11+ (API 30+) package visibility filtering can make
  `getInstalledPackages(...)` return a filtered set when the manifest does not
  declare the needed package visibility queries or `QUERY_ALL_PACKAGES`.
- Do not promise a complete inventory of all installed apps on Android 11+
  unless the app's manifest/package visibility allows it.
- Store and print a field such as `package_visibility_note` when results may be
  filtered.
- If the user asks why some apps are missing, explain that Android package
  visibility is manifest/policy controlled and cannot be fixed from a
  runtime-only snippet.
- Do not request `QUERY_ALL_PACKAGES` at runtime; it is a manifest/policy
  matter, not a dangerous runtime permission prompt.
