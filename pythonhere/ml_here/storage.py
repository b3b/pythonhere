"""Find ML model files managed by PythonHere."""

import os
import sys


def _android_models_directory():
    """Return the model directory belonging to the running Android app."""

    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity
    if activity is None:
        raise RuntimeError("A running PythonHere activity is required")

    external_files = activity.getExternalFilesDir(None)
    if external_files is None:
        raise RuntimeError("Android external app storage is unavailable")

    return os.path.join(str(external_files.getAbsolutePath()), "models")


def _is_android():
    return sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ


def models_directory(create=False):
    """Return PythonHere's platform-specific model directory.

    Android uses the app-specific external files directory. Linux uses
    PythonHere's per-user application data directory.
    """

    if _is_android():
        path = _android_models_directory()
    else:
        path = os.path.expanduser("~/.local/share/pythonhere/models")

    path = os.path.abspath(path)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def _relative_parts(value, label):
    """Return safe POSIX-style path components for a remote identifier."""

    parts = value.split("/")
    if not value or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{label} must be a relative path without dot components")
    return parts


def model_path(repo_id, filename):
    """Return the local path for a model identified by repository and file."""

    path = os.path.join(
        models_directory(),
        *_relative_parts(repo_id, "repo_id"),
        *_relative_parts(filename, "filename"),
    )
    return os.path.abspath(path)


def require_model(repo_id, filename):
    """Return an installed model path, or raise ``FileNotFoundError``."""

    path = model_path(repo_id, filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"ML model is not installed: {repo_id}/{filename} ({path})"
        )
    return path


def _model_extensions(extensions):
    """Normalize an optional model-extension filter."""

    if extensions is None:
        return None
    if isinstance(extensions, str):
        extensions = (extensions,)

    normalized = set()
    for extension in extensions:
        if not isinstance(extension, str) or not extension:
            raise ValueError("extensions must contain non-empty strings")
        normalized_extension = extension.lower()
        normalized.add(
            normalized_extension
            if normalized_extension.startswith(".")
            else f".{normalized_extension}"
        )
    return tuple(sorted(normalized))


def _discover_directory(directory, extensions):
    """Yield model files recursively beneath a directory."""

    path = os.path.abspath(os.fspath(directory))
    if not os.path.isdir(path):
        return

    def ignore_error(_error):
        pass

    for root, directories, files in os.walk(path, onerror=ignore_error):
        directories.sort(key=str.casefold)
        for filename in files:
            lower_filename = filename.lower()
            if lower_filename.endswith((".part", ".part.json")):
                continue
            if extensions is None or lower_filename.endswith(extensions):
                yield os.path.abspath(os.path.join(root, filename))


def discover_models(extra_directories=(), *, extensions=".litertlm"):
    """Find local model files, optionally filtered by filename extension.

    ``extensions`` may be one extension or an iterable, with or without the
    leading dot. The default finds LiteRT-LM models. Pass ``None`` to return
    all completed files. Temporary files belonging to an in-progress download
    are always ignored.
    """

    if isinstance(extra_directories, (str, bytes, os.PathLike)):
        extra_directories = (extra_directories,)
    extensions = _model_extensions(extensions)

    models = []
    seen = set()
    for directory in (models_directory(), *extra_directories):
        for discovered_path in _discover_directory(directory, extensions):
            key = os.path.normcase(discovered_path)
            if key not in seen:
                seen.add(key)
                models.append(discovered_path)
    return sorted(
        models,
        key=lambda path: (os.path.basename(path).casefold(), path.casefold()),
    )


__all__ = ("discover_models", "model_path", "models_directory", "require_model")
