## Pyjnius

`jnius` is installed.

Rules:

- Import Java classes with `from jnius import autoclass`.
- For Java callbacks/listeners implemented in Python, import and use
  `PythonJavaClass` and `java_method`. A plain Python class with a matching
  method name is not a Java interface implementation.
- Import `cast` only when the generated code actually uses it.
- Do not import Android app classes directly from `jnius`. For example, do not
  write `from jnius import PythonService`; use
  `autoclass("org.kivy.android.PythonService")` inside the fallback path.
- Import optional Android classes, such as `org.kivy.android.PythonService`,
  only inside the fallback path where they are needed.
- Use `cast` only when a Java API requires a specific declared type.
- Keep Java object references local unless the user needs to inspect them later.
- Convert Java strings to Python strings with `str(...)` before storing results.
- Treat Java arrays and lists defensively: they may be `None`; iterate only after
  checking.
- Java arrays are Python-indexable in Pyjnius. Use `len(java_array)` and
  `java_array[index]`. Do not call `.size()` or `.get()` unless the object is a
  Java `List`.
- For Java long bitmasks, Python `int` values are acceptable.
- Catch narrow exceptions only around optional Android fields or deprecated APIs.
  Do not hide collection-wide failures.
- If catching an exception for one package/item, store a readable error string in
  that item and continue.
- Do not use Pyjnius to launch external processes.
- Do not reference Android class constants from a variable that has not been
  assigned with `autoclass`.

Pyjnius arrays:
- Use Python lists, bytes, or bytearray for Java array arguments.
- Do not invent imports like `jarray`.
- If a Java API needs a writable output buffer, use a mutable Python list or bytearray and check the method’s return value.

Pyjnius object conversion rules:

- Do not assume Python string conversion of Java objects produces valid Android
  values.
- Convert Java `String` objects to Python strings with `str(...)` before storing
  ordinary text results, but do not use Python `str(...)` for Android object
  identifiers that have their own Java string form, such as `Uri`.
- For Java objects with Android-specific string forms, call the Java method
  `toString()`.
- For `android.net.Uri`, prefer keeping the Java `Uri` object and passing it
  directly to Android APIs such as `ContentResolver.openInputStream(uri)`.
- Do not convert Java `android.net.Uri` objects with Python `str(uri)`.
  In Pyjnius, `str(uri)` may produce a Python object representation like
  `<android.net.Uri at 0x... jclass=android/net/Uri ...>` instead of a valid
  `content://...` URI string.
- If a Java `Uri` must be stored as text, use `uri.toString()`, not `str(uri)`.
- Never parse a Pyjnius object representation as a URI.
- Any generated code that logs or displays a URI should log both the media ID
  and `uri.toString()`, not the Python object representation.

Wrong:

```python
content_uri = ContentUris.withAppendedId(ImagesMedia.EXTERNAL_CONTENT_URI, image_id)
photos.append({"id": image_id, "uri": str(content_uri)})

uri = Uri.parse(photo["uri"])
stream = resolver.openInputStream(uri)
```

Correct, preferred:

```python
content_uri = ContentUris.withAppendedId(ImagesMedia.EXTERNAL_CONTENT_URI, image_id)
photos.append({"id": image_id, "uri": content_uri})

stream = resolver.openInputStream(photo["uri"])
```

Correct, if serialization is needed:

```python
content_uri = ContentUris.withAppendedId(ImagesMedia.EXTERNAL_CONTENT_URI, image_id)
photos.append({"id": image_id, "uri": content_uri.toString()})

Uri = autoclass("android.net.Uri")
uri = Uri.parse(photo["uri"])
stream = resolver.openInputStream(uri)
```

Pyjnius Java class access rules:

- Do not call Java classes through undefined Python package names.
- Every Java class used must be bound with `autoclass(...)`.
- Do not assume Java package names are available as Python modules.

Wrong:

```python
android.graphics.Bitmap.createScaledBitmap(bitmap, new_w, new_h, True)
```

Correct:

```python
Bitmap = autoclass("android.graphics.Bitmap")
scaled_bitmap = Bitmap.createScaledBitmap(bitmap, new_w, new_h, True)
```

Nested Java classes:

- In Pyjnius, nested Java classes must be imported with `$` using `autoclass`.
  Do not access nested Java classes as Python attributes of the parent class.

Correct:

```python
VERSION = autoclass("android.os.Build$VERSION")
BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")
CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
PackageInfoFlags = autoclass("android.content.pm.PackageManager$PackageInfoFlags")
ImagesMedia = autoclass("android.provider.MediaStore$Images$Media")
```

Incorrect:

```python
Build.VERSION.SDK_INT
BitmapFactory.Options()
Bitmap.CompressFormat
PackageManager.PackageInfoFlags
MediaStore.Images.Media
```

Android version checks:

- Use:

```python
VERSION = autoclass("android.os.Build$VERSION")
SDK_INT = VERSION.SDK_INT
```

- Do not use:

```python
Build.VERSION.SDK_INT
```

because Pyjnius does not reliably expose nested classes as Python attributes.

Nullable Java constants:

- Treat Android Java class constants returned through Pyjnius as nullable.
  Some constants may be `None` even when the Android API normally defines them.
- Never pass unchecked Pyjnius constants into Android APIs that expect strings,
  arrays of strings, column names, permissions, selection clauses, sort orders,
  file modes, or intent actions.
- Before using a Java string constant in `projection`, `selection`, `sortOrder`,
  `getColumnIndex(...)`, `Intent(...)`, or permission checks, resolve it to a
  non-null Python string.

Correct:

```python
ImagesMedia = autoclass("android.provider.MediaStore$Images$Media")

COL_ID = ImagesMedia._ID or "_id"
COL_DATE_ADDED = ImagesMedia.DATE_ADDED or "date_added"
COL_DATE_TAKEN = ImagesMedia.DATE_TAKEN or "datetaken"
COL_DISPLAY_NAME = ImagesMedia.DISPLAY_NAME or "_display_name"
COL_BUCKET = ImagesMedia.BUCKET_DISPLAY_NAME or "bucket_display_name"

projection = [COL_ID, COL_DATE_ADDED]
sort_order = COL_DATE_ADDED + " DESC"
```

Incorrect:

```python
projection = [ImagesMedia._ID, ImagesMedia.DATE_TAKEN]
sort_order = f"{ImagesMedia.DATE_TAKEN} DESC"
selection = ImagesMedia.BUCKET_DISPLAY_NAME + " = ?"
```

- Never allow `None` inside Java `String[]` arguments or string parameters.
  This includes MediaStore projections, selection args, sort order strings, and
  cursor column names.
- If an Android API throws a Java `NullPointerException` mentioning
  `String.toLowerCase()` during a query, suspect a `None` column name or string
  argument passed from Pyjnius.
- Prefer explicit fallback strings for well-known Android column names rather
  than raw constants when generating resilient code.

Bitmap-related Pyjnius rules:

- For bitmap decode options, use:

```python
BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")
opts = BitmapFactoryOptions()
```

- Never use:

```python
opts = BitmapFactory.Options()
```

- For bitmap compression format, use:

```python
CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
bitmap.compress(CompressFormat.JPEG, 85, output_stream)
```

- Never use:

```python
Bitmap.CompressFormat.JPEG
```


Android MediaStore and shared-media Pyjnius rules:

- Prefer MediaStore content URIs over raw filesystem paths.
- Do not depend on the `_data` column for gallery/media access.
- Query `_id`, build a content URI, then decode through `ContentResolver`.
- Keep the Java `Uri` object directly or store URI text with `uri.toString()`.
  Do not store `str(uri)`.
- Do not filter only by `bucket_display_name = "Camera"` unless the user
  specifically asked for the Camera folder only. For a general gallery, query
  all images first, then add filters only after the broad query is confirmed
  working.
- Always handle `cursor is None` and `cursor.getCount() == 0`.
- Always close the cursor in `finally`.
- If a thumbnail decode fails for one item, store/log a readable item-level
  error and continue with other items.

Preferred MediaStore URI pattern:

```python
ContentUris = autoclass("android.content.ContentUris")
ImagesMedia = autoclass("android.provider.MediaStore$Images$Media")
BitmapFactory = autoclass("android.graphics.BitmapFactory")
BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")

content_uri = ContentUris.withAppendedId(
    ImagesMedia.EXTERNAL_CONTENT_URI,
    image_id,
)

opts = BitmapFactoryOptions()
stream = resolver.openInputStream(content_uri)
try:
    bitmap = BitmapFactory.decodeStream(stream, None, opts)
finally:
    if stream is not None:
        stream.close()
```

Avoid as the default:

```python
path = cursor.getString(cursor.getColumnIndex("_data"))
bitmap = BitmapFactory.decodeFile(path, opts)
```

Android media permission and special-access rules:

- Declaring a permission in `buildozer.spec` or `AndroidManifest.xml` does not
  prove it is granted at runtime.
- For Android 13+ image access, check/request
  `android.permission.READ_MEDIA_IMAGES`.
- For Android 13+ video access, check/request
  `android.permission.READ_MEDIA_VIDEO`.
- For Android 13+ audio access, check/request
  `android.permission.READ_MEDIA_AUDIO`.
- For Android 12 and below, check/request
  `android.permission.READ_EXTERNAL_STORAGE`.
- Do not rely on `WRITE_EXTERNAL_STORAGE` for reading shared photos on modern
  Android.
- Do not check `MANAGE_EXTERNAL_STORAGE` with `check_permission(...)`.
  It is special Android settings access, not a normal runtime permission.
- For arbitrary `/sdcard`, `/sdcard/DCIM`, `/sdcard/Download`, or full
  shared-storage browsing on Android 11+, check
  `Environment.isExternalStorageManager()`.
- If all-files access is needed and not enabled, open
  `Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION` with
  `Uri.parse("package:" + activity.getPackageName())`. If that fails, fall back
  to `Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION`.

Thumbnail and cache rules:

- Write generated thumbnails into the app cache directory from
  `context.getCacheDir().getAbsolutePath()`.
- Do not use `Path.cwd() / "gallery_cache"` for Android cache files.
- Kivy `Image.source` should point to a real cache file path.
- Do not assume Kivy supports `data:image/...;base64,...` sources.
- Use separate constants for UI size and bitmap decode size, for example
  `THUMB_UI_DP = dp(120)` and `THUMB_PX = 240`.
- Do not pass `dp(...)` floats into Android bitmap APIs.
- Android bitmap dimensions and sample sizes must be plain Python `int` values.
- Recycle Android `Bitmap` objects after thumbnail compression when possible.

Media/gallery error-reporting rules:

- Do not hide media/gallery failures behind generic messages like
  `Error loading photos. Check logs.`
- Generated code should show the real failure stage and exception message in the
  UI during development.
- Background workers should return structured results such as
  `{ "ok": False, "stage": "decode_thumbnail", "error": "AttributeError: ..." }`.
- Logs may include full stack traces, but logs must not be the only place where
  the real problem appears.

General forbidden Pyjnius patterns:

Never generate:

```python
BitmapFactory.Options()
Bitmap.CompressFormat
Build.VERSION
MediaStore.Images.Media
PackageManager.PackageInfoFlags
projection = [SomeJavaClass.SOME_COLUMN]
sort_order = f"{SomeJavaClass.SOME_COLUMN} DESC"
```

Generate:

```python
BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")
CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
VERSION = autoclass("android.os.Build$VERSION")
ImagesMedia = autoclass("android.provider.MediaStore$Images$Media")
PackageInfoFlags = autoclass("android.content.pm.PackageManager$PackageInfoFlags")

COL = SomeJavaClass.SOME_COLUMN or "known_fallback_name"
projection = [COL]
sort_order = COL + " DESC"
```

For Android package APIs:

- `PackageManager.GET_PERMISSIONS` requests permission metadata.
- Android API 33 and newer require
  `android.content.pm.PackageManager$PackageInfoFlags.of(flags)`.
- In Pyjnius, define:

```python
PackageInfoFlags = autoclass("android.content.pm.PackageManager$PackageInfoFlags")
```

and call:

```python
PackageInfoFlags.of(flags)
```

- Do not access it as:

```python
PackageManager.PackageInfoFlags
```

- Older APIs accept integer flags.
- System-app flags come from `android.content.pm.ApplicationInfo`.
  Use `ApplicationInfo.FLAG_SYSTEM` and `ApplicationInfo.FLAG_UPDATED_SYSTEM_APP`.
  Do not use `android.content.pm.ActivityInfo` for this.
- Permission grant status comes from
  `android.content.pm.PackageInfo.REQUESTED_PERMISSION_GRANTED`, not from
  `PackageManager.PERMISSION_GRANTED` and not from `ActivityInfo`.
- If checking requested permission grant status, define:

```python
PackageInfo = autoclass("android.content.pm.PackageInfo")
```

before using that constant.
- Version code should use `longVersionCode` when present and fall back to
  `versionCode`.

Additional forbidden Pyjnius media patterns:

Never generate:

```python
str(content_uri)
Uri.parse(str(content_uri))
photos.append({"uri": str(content_uri)})
android.graphics.Bitmap.createScaledBitmap(bitmap, new_w, new_h, True)
Path.cwd() / "gallery_cache"
show_error("Error loading photos. Check logs.")
return None  # after catching a media/gallery exception
cursor.getString(cursor.getColumnIndex("_data"))  # as the primary media access path
```

Generate:

```python
photos.append({"uri": content_uri})
# or, only if text serialization is required:
photos.append({"uri": content_uri.toString()})

Bitmap = autoclass("android.graphics.Bitmap")
scaled_bitmap = Bitmap.createScaledBitmap(bitmap, new_w, new_h, True)

cache_dir = context.getCacheDir().getAbsolutePath()

return {
    "ok": False,
    "stage": stage,
    "error": f"{type(e).__name__}: {e}",
}
```

Pyjnius overload and Android intent safety:
- When Java APIs have overloaded constructors or methods, prefer the least
  ambiguous call pattern through Pyjnius. For Android `Intent`, create
  `intent = Intent(action)` and then call setters such as `setData(...)`,
  `setType(...)`, or `putExtra(...)` rather than relying on overloaded
  constructors.
- Do not pass Python `None` where Android expects a Java `String`, `String[]`,
  `Uri`, `Intent`, `Context`, or callback/listener.
- When an API expects a Java primitive array or Java collection, prefer normal
  Python lists only when Pyjnius is known to convert them for that method.
  Otherwise use the Android/Python-for-Android helper API if one exists.
- For nullable Android constants, resolve to non-null Python strings before
  passing them into Android APIs.
- Keep Settings/Intent launch results in a named global and report whether
  `startActivity(...)` was attempted; do not claim the requested setting changed
  just because the Settings screen opened.
