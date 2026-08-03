## Android Permissions

Use this section when need to check, request, or explain permissions for
the running Android app.

Critical rules:

- Do not assume a runtime permission can be granted if it is missing from the
  Android manifest. Runtime requests only work for permissions declared by the
  app.
- Do not use installed-package permission metadata to decide whether this app has
  a runtime permission. Use runtime permission APIs for the current app.
- Choose the Android access mechanism from the user's goal. Do not force every
  access request through `request_permissions`.
- Use fully qualified Android permission strings for all permission APIs, for
  example `"android.permission.CAMERA"`. Do not pass short names such as
  `"CAMERA"`, `"READ_EXTERNAL_STORAGE"`, or `"WRITE_EXTERNAL_STORAGE"` to
  `check_permission`, `request_permissions`, or `context.checkSelfPermission`.
- If storing display-friendly names, keep them separate from the full permission
  strings used for Android API calls.
- When the user asks to "request", "enable", "grant", or "get access", generated
  code must perform the appropriate request action immediately when possible. Do
  not tell the user to ask again for the Settings-opening step.
- Do not call `raise SystemExit` or terminate the host app when context,
  activity, or permission APIs are unavailable. Store an error result and print a
  concise message instead.

Decision model:

- Dangerous runtime permissions: check with `check_permission(...)` or
  `context.checkSelfPermission(...)`; request with
  `android.permissions.request_permissions(...)` when the user asks to request.
  Examples: camera, microphone, fine/coarse location, contacts, calendar,
  nearby Bluetooth permissions, Android 13+ notifications.
- Normal permissions: do not request at runtime. Report that they are install-
  time permissions.
- Signature/privileged permissions: do not request at runtime. Report that they
  cannot be granted to ordinary apps unless the app is privileged or signed with
  the platform key.
- Special app-access permissions: do not request with
  `request_permissions(...)`. Check with the dedicated Android API when one
  exists, and open the relevant Settings screen only when the user asks to
  request/open/enable access.
- Storage and media access depends on Android API level and requested scope.
  Do not treat "storage", "sdcard", "external storage", "photos", "media", or
  "all files" as one generic permission.

Preferred Python-for-Android API:

- Prefer `from android.permissions import Permission, check_permission,
  request_permissions` when the `android` package is available.
- Use `check_permission(permission_name)` to check one permission for the current
  app.
- Use `request_permissions(permission_names, callback)` to request one or more
  dangerous runtime permissions.
- Pass full permission strings to these functions. Prefer constants from
  `android.permissions.Permission` when they are available and correct for the
  target API; otherwise use full strings like
  `"android.permission.ACCESS_FINE_LOCATION"`.
- The request callback should accept `(permissions, grants)` and store both the
  raw arrays and a Python dictionary mapping permission name to granted boolean.
- Do not rely on `print(...)` inside the permission request callback as the only
  result. The callback may run after `there run` output capture has ended. Store the
  result globally and update visible UI when appropriate.
- Do not convert grant values with `bool(grant)`. Android uses
  `PackageManager.PERMISSION_GRANTED == 0` and
  `PackageManager.PERMISSION_DENIED == -1`, so `bool(-1)` is wrong. Convert with
  `grant == PackageManager.PERMISSION_GRANTED` when grant values are integers.
- Keep a global reference to the callback result, for example
  `android_permission_request_result`, so later `there` commands can inspect it.

Pyjnius fallback for checks:

- Get a current context from `org.kivy.android.PythonActivity.mActivity` or, only
  as a fallback, `org.kivy.android.PythonService.mService`.
- Define `VERSION = autoclass("android.os.Build$VERSION")` and use
  `VERSION.SDK_INT`. Do not use `Build.VERSION.SDK_INT`.
- Define `PackageManager = autoclass("android.content.pm.PackageManager")`.
- On API 23 and newer, call `context.checkSelfPermission(permission_name)` and
  compare the result to `PackageManager.PERMISSION_GRANTED`.
- For permission request callbacks, use the same
  `PackageManager.PERMISSION_GRANTED` constant to normalize grant results.
- On API levels below 23, runtime permission prompts do not exist. Treat declared
  install-time permissions as already granted for runtime-check purposes, but
  print that the result is pre-runtime-permission behavior.

Requesting permissions:

- For Kivy/Python-for-Android apps, use `android.permissions.request_permissions`
  instead of calling `activity.requestPermissions(...)` directly.
- If the `android.permissions` module is unavailable, do not invent a Pyjnius
  subclass or callback receiver for `activity.requestPermissions(...)`. Use
  Pyjnius only to check current permission state, then report that requesting
  runtime permissions requires the Python-for-Android permission helper or app
  integration.
- Request only dangerous/runtime permissions. Normal permissions are granted at
  install time and should be reported as not needing a runtime prompt.
- Do not request special app-access permissions as if they were normal runtime
  permissions. Examples: `MANAGE_EXTERNAL_STORAGE`, notification listener
  access, accessibility service access, overlay permission, battery optimization
  exemption, usage access, and exact alarm access. If the user asked only to
  check, report that they require a Settings screen flow. If the user asked to
  request/enable/get access, open the correct Settings screen immediately when a
  foreground activity is available.
- Android 13+ notification permission is
  `android.permission.POST_NOTIFICATIONS`; request it only on API 33 and newer.
- If the activity is unavailable, do not attempt a permission request from a
  service-only context. Print that a foreground activity is required.

Special app-access flows:

- If the user asks to request or enable a special app-access permission, open the
  most specific Settings screen available for this app. Use `Intent`,
  `Settings`, and `Uri.parse(f"package:{context.getPackageName()}")` where the
  action supports an app-specific URI.
- Build Settings intents conservatively: create `intent = Intent(action)` and
  then call `intent.setData(Uri.parse(f"package:{package_name}"))` for
  app-specific Settings actions. This is more reliable through Pyjnius than
  relying on overloaded Java constructors.
- Always store whether the Settings screen was opened, the action used, and the
  current access state before opening Settings.
- Do not claim Settings access was granted immediately after opening Settings.
  The user must return from Settings; tell them to rerun the check afterward.
- If `activity` is unavailable, do not call `startActivity`. Report that a
  foreground activity is required to open Settings.

Storage and media access:

- For Android 13+ (API 33+), media permissions are split:
  `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`, and `READ_MEDIA_AUDIO`. Use these
  only for media-library access, not for arbitrary `/sdcard` file access.
- For Android 10-12 (API 29-32), `READ_EXTERNAL_STORAGE` may allow media/shared
  storage reads, but scoped storage still limits arbitrary file access. Do not
  promise full `/sdcard` traversal from this permission.
- `WRITE_EXTERNAL_STORAGE` is ignored or heavily limited on modern Android. Do
  not rely on it for Android 10+ shared-storage writes.
- When generating runtime storage permission requests, request
  `android.permission.WRITE_EXTERNAL_STORAGE` only for API 28 and lower. For API
  29, do not request `WRITE_EXTERNAL_STORAGE` as a solution for broad storage
  writes; explain the scoped-storage limitation instead.
- For Android 11+ (API 30+), broad "all files" access is the special access
  `MANAGE_EXTERNAL_STORAGE`. Check it with
  `Environment.isExternalStorageManager()`.
- To request Android 11+ all-files access, open Settings; do not call
  `request_permissions(["android.permission.MANAGE_EXTERNAL_STORAGE"], ...)`.
  Prefer `Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION` with
  `Uri.parse(f"package:{context.getPackageName()}")`, and fall back to
  `Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION` if the app-specific
  action fails.
- For a broad `/sdcard` access request on Android 11+, do not additionally
  request `READ_EXTERNAL_STORAGE` or `WRITE_EXTERNAL_STORAGE` as the primary
  solution. Those permissions do not grant broad all-files access.
- For Android versions below 11, use runtime storage permissions only when they
  match the user's requested scope, and explain that behavior differs by API
  level and manifest settings.
- For creating or picking user-selected files, prefer Android's document/media
  picker or Storage Access Framework when the user does not need broad all-files
  access.

Output shape:

- For permission checks, use a global such as `android_permission_status`.
- For permission requests, use a global such as
  `android_permission_request_result`.
- Print each permission with a short status such as `granted`, `denied`,
  `not_requested_pre_23`, `normal_permission_no_runtime_prompt`, or
  `requires_settings_flow`.
- For special Settings flows, include fields such as `access_name`,
  `currently_granted`, `settings_opened`, `settings_action`, and
  `rerun_check_after_return`.

Android 14+ selected media access:

- On Android 14+ (API 34+), users may grant partial access to selected
  photos/videos. Treat this as a valid limited-access state, not a simple
  denial.
- For media-gallery code on Android 14+, consider
  `android.permission.READ_MEDIA_VISUAL_USER_SELECTED` alongside
  `READ_MEDIA_IMAGES` and/or `READ_MEDIA_VIDEO` when the user wants to manage or
  reselect partial media access.
- If the user only wants to pick one or a few files/photos, prefer a
  picker/user-selection flow instead of broad media permissions.
- If partial media access is detected, explain through code comments or status
  text that MediaStore results may include only the selected items.

Notification and special-access reminders:

- `android.permission.POST_NOTIFICATIONS` is a dangerous runtime permission only
  on API 33+; below API 33, do not request it at runtime.
- Exact alarm, overlay, accessibility, notification listener, usage access,
  battery optimization exemption, and all-files access are special settings
  flows, not normal runtime permissions.
- For Settings flows, open the specific settings screen only when the user asked
  to request, enable, or open access; otherwise only report the current state and
  the needed flow.
