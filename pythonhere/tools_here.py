"""Reusable tools for the live PythonHere runtime."""

import math
import threading
from pathlib import Path
from typing import Any

DEFAULT_UI_SNAPSHOT_DEPTH = 6
DEFAULT_UI_SNAPSHOT_WIDGETS = 200
MAX_UI_SNAPSHOT_CLASS = 120
MAX_UI_SNAPSHOT_DEPTH = 48
MAX_UI_SNAPSHOT_WIDGETS = 500
MAX_UI_SNAPSHOT_TEXT = 240


def _require_main_thread() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("This PythonHere tool must run on Kivy's main thread")


def _current_root(widget=None):
    if widget is not None:
        return widget

    from kivy.app import App
    from kivy.core.window import Window

    app = App.get_running_app()
    if app is not None and app.root is not None:
        return app.root
    if Window.children:
        return Window.children[0]
    raise RuntimeError("PythonHere has no visible root widget")


def _json_number(value):
    number = float(value)
    if not math.isfinite(number):
        return None
    return round(number, 2)


def _snapshot_limit(name: str, value: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _optional_text(widget):
    try:
        value = widget.text
        return (str(value) if value is not None else None), False
    except AttributeError:
        return None, False
    except Exception:  # A custom diagnostic property must not abort the snapshot.
        return None, True


def _snapshot_widget(current, path):
    children = list(reversed(getattr(current, "children", ())))
    text, text_unavailable = _optional_text(current)
    text_truncated = bool(text is not None and len(text) > MAX_UI_SNAPSHOT_TEXT)
    if text_truncated:
        text = text[: MAX_UI_SNAPSHOT_TEXT - 3] + "..."

    class_name = type(current).__name__
    class_truncated = len(class_name) > MAX_UI_SNAPSHOT_CLASS
    if class_truncated:
        class_name = class_name[: MAX_UI_SNAPSHOT_CLASS - 3] + "..."

    item = {
        "path": path,
        "class": class_name,
        "text": text,
        "disabled": bool(getattr(current, "disabled", False)),
        "pos": [_json_number(value) for value in current.pos],
        "size": [_json_number(value) for value in current.size],
        "child_count": len(children),
    }
    if class_truncated:
        item["class_truncated"] = True
    if text_unavailable:
        item["text_unavailable"] = True
    if text_truncated:
        item["text_truncated"] = True
    return item, children


def snapshot_ui(
    widget=None,
    *,
    max_depth: int = DEFAULT_UI_SNAPSHOT_DEPTH,
    max_widgets: int = DEFAULT_UI_SNAPSHOT_WIDGETS,
) -> dict[str, Any]:
    """Return observable widget facts; call only on Kivy's main thread."""
    _require_main_thread()
    max_depth = _snapshot_limit(
        "max_depth",
        max_depth,
        0,
        MAX_UI_SNAPSHOT_DEPTH,
    )
    max_widgets = _snapshot_limit(
        "max_widgets",
        max_widgets,
        1,
        MAX_UI_SNAPSHOT_WIDGETS,
    )
    root = _current_root(widget)
    widgets = []
    pending = [("0", root, 0)]
    omitted_descendants = False

    while pending and len(widgets) < max_widgets:
        path, current, depth = pending.pop()
        item, children = _snapshot_widget(current, path)
        widgets.append(item)

        if depth >= max_depth:
            omitted_descendants = omitted_descendants or bool(children)
        else:
            for index in range(len(children) - 1, -1, -1):
                pending.append((f"{path}/{index}", children[index], depth + 1))

    return {
        "widgets": widgets,
        "widget_count": len(widgets),
        "truncated": omitted_descendants or bool(pending),
    }


def runtime_info(app=None, root=None) -> dict[str, Any]:
    """Return live Kivy runtime information; call only on its main thread."""
    _require_main_thread()
    import kivy
    from kivy.app import App
    from kivy.core.window import Window
    from kivy.utils import platform

    if app is None:
        app = App.get_running_app()
    root = _current_root(root)
    return {
        "app_class": type(app).__name__ if app is not None else None,
        "root_class": type(root).__name__,
        "kivy_version": kivy.__version__,
        "platform": platform,
        "window_size": [_json_number(value) for value in Window.size],
    }


def save_screenshot(
    path: str | Path = "pythonhere-screenshot.png",
    widget=None,
) -> str:
    """Save visible content as PNG; call only on Kivy's main thread."""
    _require_main_thread()
    from kivy.app import App
    from window_here import save_screenshot as save_window_screenshot

    destination = Path(path)
    if not destination.is_absolute():
        app = App.get_running_app()
        upload_dir = getattr(app, "upload_dir", None) if app is not None else None
        destination = Path(upload_dir or Path.cwd()) / destination
    return save_window_screenshot(destination, widget=widget)


def encoded_screenshot(widget=None) -> str:
    """Encode visible content as PNG; call only on Kivy's main thread."""
    _require_main_thread()
    from window_here import encoded_screenshot as encode_window_screenshot

    return encode_window_screenshot(widget=widget)


def pin_shortcut(script: str, label: str | None = None) -> None:
    """Request an Android launcher shortcut for a PythonHere script."""
    _require_main_thread()
    from android_here import pin_shortcut as pin_android_shortcut

    shortcut_label = label or script.rstrip("/").rsplit("/", 1)[-1]
    pin_android_shortcut(script=script, label=shortcut_label)


__all__ = (
    "encoded_screenshot",
    "pin_shortcut",
    "runtime_info",
    "save_screenshot",
    "snapshot_ui",
)
