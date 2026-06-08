## Android Media And Files

Use this section when the user asks to browse, display, scan, filter, or build a
gallery from Android photos, videos, downloads, `/sdcard`, DCIM, Pictures,
Movies, Music, or other shared-storage paths.

Permissions and storage access:

- Always check actual runtime permission state before assuming media or storage access exists.
- For Android 13+ media-library access, use granular media permissions such as
  `android.permission.READ_MEDIA_IMAGES` and/or
  `android.permission.READ_MEDIA_VIDEO`.
- For older Android versions, `READ_EXTERNAL_STORAGE` may still be relevant.
- Do not rely on `WRITE_EXTERNAL_STORAGE` for reading photos on modern Android.
- Do not call `check_permission("android.permission.MANAGE_EXTERNAL_STORAGE")`.
  It is a special app-access setting, not a normal runtime permission.
- On Android 11+ broad all-files access can be checked with
  `Environment.isExternalStorageManager()`, but a false result does not by
  itself prove every media path is unreadable. Probe the requested path and
  report both facts.
- Do not assume `MANAGE_EXTERNAL_STORAGE` is available just because it is present
  in the manifest. The user usually must enable “All files access” in system
  settings, and Play policy restricts this permission.
- Prefer privacy-friendly media access through MediaStore or the system photo
  picker unless the user specifically asks for direct filesystem browsing.
- Store the error/status and show errors.

Path vs MediaStore access:

- For a concrete path such as `/sdcard/DCIM/Camera`, first probe that path
  directly before deciding the app lacks access.
- For media-library/gallery access, prefer MediaStore queries.
- Do not depend on the MediaStore `_data` column. It can be missing, deprecated,
  inaccessible, or point to a file path the app cannot decode directly.
- Prefer querying `_id`, building a `content://` URI with
  `ContentUris.withAppendedId(...)`, and reading through
  `context.getContentResolver().openInputStream(uri)`.
- Decode MediaStore images from a valid Android `Uri` or input stream, not from
  guessed filesystem paths.
- If direct path access is used as a fallback, treat failure to read/decode as a
  normal state and continue.

MediaStore querying:

- Always handle `cursor is None`.
- Always check `cursor.getCount()` and show an empty-state UI when it is zero.
- Use `moveToFirst()` safely before reading rows.
- Always close the cursor in `finally`.
- Avoid `while cursor.isAfterLast() is False`; prefer clearer logic such as:
  `if cursor.moveToFirst(): ... while not cursor.isAfterLast(): ...`.
- Log counts separately:
  - rows found
  - thumbnails attempted
  - thumbnails decoded
  - thumbnails failed
  - permission/access state

HEIC and thumbnails:

- Kivy `Image` may not load `.heic` directly on Android.
- Use Android image decoding APIs such as `android.graphics.BitmapFactory` or
  `android.graphics.ImageDecoder` for HEIC thumbnails when available.
- Import nested Android classes with `$`. For bitmap decoding options, define
  `BitmapFactoryOptions = autoclass("android.graphics.BitmapFactory$Options")`
  and use `BitmapFactoryOptions()`. Do not access it as `BitmapFactory.Options()`.
- With `ImageDecoder` and a Java `File`, prefer:
  `source = ImageDecoder.createSource(java_file)`.
- Do not call:
  `ImageDecoder.createSource(context.getContentResolver(), java_file)`,
  because the `ContentResolver` overload expects a `Uri`, not a `File`.
- If using a `ContentResolver` with `ImageDecoder`, pass a valid Android `Uri`,
  not a filesystem path or Java `File`.
- Avoid `ImageDecoder.decodeBitmap(source, python_lambda)` unless a correct Java
  listener interface is implemented. Through Pyjnius, prefer:
  `bitmap = ImageDecoder.decodeBitmap(source)`,
  then scale/compress the decoded bitmap.
- Import nested Android classes with `$`. For bitmap compression, define:
  `CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")`
  and use `CompressFormat.JPEG` or `CompressFormat.PNG`.
- Do not access compression format as `Bitmap.CompressFormat`.
- Do not assume Kivy `Image.source` accepts `data:image/...;base64,...` URIs.
  Prefer writing thumbnails to small temporary files in the app cache directory
  and setting `Image.source` to those file paths.
- Use `context.getCacheDir().getAbsolutePath()` for thumbnail cache files.
- Avoid writing into `/sdcard` unless the user asks for exported files.
- Keep Android bitmap dimensions as plain Python `int` pixel values.
- Do not pass Kivy `dp(...)` float values directly to Android bitmap APIs such
  as `Bitmap.createScaledBitmap(...)`.
- Use separate constants for UI size and decode size, for example:
  `THUMB_UI_DP = dp(120)` for widgets and `THUMB_PX = 240` for Android bitmap
  scaling.
- Recycle Android `Bitmap` objects after thumbnail compression when possible.

Generated-code defaults:

- For “show my gallery/photos” code, default to:
  MediaStore query → `_id` → content URI → openInputStream/decode → cache
  thumbnail file → Kivy Image source = cache file path.
- Avoid defaulting to:
  MediaStore `_data` → raw filesystem path → `BitmapFactory.decodeFile(...)`.
- Include a visible debug/status label during development.
- Include enough logging to distinguish:
  permission not granted,
  MediaStore returned no rows,
  rows found but decode failed,
  thumbnails decoded but widget display failed.

Android 14+ partial photo/video access:

- On Android 14+ (API 34+), photo/video access may be partial because the user
  selected only some media. Generated gallery code must report whether access
  appears full, partial, denied, or unknown when permission information is
  available.
- If only partial access is available, continue with MediaStore and show the
  accessible subset instead of treating the result as a failure.
- When the user wants to choose media rather than browse the whole library,
  prefer a system picker/user-selection flow over broad storage/media
  permissions.
- Keep the debug/status label explicit: distinguish `permission_denied`,
  `partial_media_access`, `mediastore_empty`, `decode_failed`, and
  `display_ready`.

Query defaults:

- For general gallery requests, query images first unless the user asked for
  videos or audio too. Avoid scanning every media type by default.
- Limit initial thumbnail queries to a reasonable count such as 50-100 items,
  store full metadata in a global, and render a small preview first.
- Do not assume an empty MediaStore result means there are no photos on the
  device; report permission/access state and query filters too.
