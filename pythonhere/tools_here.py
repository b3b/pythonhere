"""Reusable tools for the live PythonHere runtime."""

import math
import threading
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

MAIN_THREAD_BRIDGE_TIMEOUT = 10.0
DEFAULT_UI_SNAPSHOT_DEPTH = 6
DEFAULT_UI_SNAPSHOT_WIDGETS = 200
MAX_UI_SNAPSHOT_CLASS = 120
MAX_UI_SNAPSHOT_DEPTH = 48
MAX_UI_SNAPSHOT_WIDGETS = 500
MAX_UI_SNAPSHOT_TEXT = 240


class MainThreadBridgeError(RuntimeError):
    """Kivy could not execute a requested main-thread operation."""


class MainThreadTimeoutError(MainThreadBridgeError):
    """Kivy did not execute a requested operation before its deadline."""


def _clock_boundary():
    """Return the Kivy Clock objects used by the worker-thread bridge."""
    from kivy.clock import Clock, ClockNotRunningError

    return Clock, ClockNotRunningError


def _run_on_main_thread(function, /, *args, _timeout=None, **kwargs):
    """Run ``function`` on Kivy's thread and synchronously return its result."""
    if threading.current_thread() is threading.main_thread():
        return function(*args, **kwargs)

    timeout = MAIN_THREAD_BRIDGE_TIMEOUT if _timeout is None else _timeout
    completion = Future()

    def execute(_delta_time):
        if not completion.set_running_or_notify_cancel():
            return
        try:
            result = function(*args, **kwargs)
        except BaseException as exc:  # Ensure every invocation releases its waiter.
            completion.set_exception(exc)
        else:
            completion.set_result(result)

    def clock_ended(_event):
        if completion.set_running_or_notify_cancel():
            completion.set_exception(
                MainThreadBridgeError(
                    "Kivy's Clock stopped before PythonHere could run the "
                    "requested main-thread operation"
                )
            )

    clock, clock_not_running_error = _clock_boundary()
    try:
        event = clock.create_lifecycle_aware_trigger(
            execute,
            clock_ended,
            timeout=0,
            release_ref=False,
        )
        event()
    except clock_not_running_error as exc:
        raise MainThreadBridgeError(
            "Kivy's Clock is not running; PythonHere cannot run the requested "
            "main-thread operation"
        ) from exc

    try:
        return completion.result(timeout=timeout)
    except FutureTimeoutError:
        # An implementation may itself raise TimeoutError. Preserve it when it
        # completed before the bridge deadline instead of mislabelling it.
        if completion.done():
            return completion.result()

        cancelled_before_start = completion.cancel()
        event.cancel()
        if cancelled_before_start:
            detail = "The operation was cancelled before it started."
        elif completion.done():
            return completion.result()
        else:
            detail = "The operation had started and may still complete."
        raise MainThreadTimeoutError(
            f"Kivy did not complete the requested main-thread operation within "
            f"{timeout:g} seconds. {detail} Do not blindly retry mutations."
        ) from None


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


def _snapshot_ui(
    widget=None,
    *,
    max_depth: int = DEFAULT_UI_SNAPSHOT_DEPTH,
    max_widgets: int = DEFAULT_UI_SNAPSHOT_WIDGETS,
) -> dict[str, Any]:
    """Return observable widget facts from Kivy's main thread."""
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


def snapshot_ui(
    widget=None,
    *,
    max_depth: int = DEFAULT_UI_SNAPSHOT_DEPTH,
    max_widgets: int = DEFAULT_UI_SNAPSHOT_WIDGETS,
) -> dict[str, Any]:
    """Return observable widget facts, marshaling worker calls to Kivy."""
    return _run_on_main_thread(
        _snapshot_ui,
        widget,
        max_depth=max_depth,
        max_widgets=max_widgets,
    )


def _runtime_info(app=None, root=None) -> dict[str, Any]:
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


def runtime_info(app=None, root=None) -> dict[str, Any]:
    """Return live Kivy runtime information, marshaling worker calls."""
    return _run_on_main_thread(_runtime_info, app, root)


def _save_screenshot(
    path: str | Path = "pythonhere-screenshot.png",
    widget=None,
) -> str:
    from kivy.app import App
    from window_here import save_screenshot as save_window_screenshot

    destination = Path(path)
    if not destination.is_absolute():
        app = App.get_running_app()
        upload_dir = getattr(app, "upload_dir", None) if app is not None else None
        destination = Path(upload_dir or Path.cwd()) / destination
    return save_window_screenshot(destination, widget=widget)


def save_screenshot(
    path: str | Path = "pythonhere-screenshot.png",
    widget=None,
) -> str:
    """Save visible content as PNG, marshaling worker calls to Kivy."""
    return _run_on_main_thread(_save_screenshot, path, widget)


def _encoded_screenshot(widget=None) -> str:
    from window_here import encoded_screenshot as encode_window_screenshot

    return encode_window_screenshot(widget=widget)


def encoded_screenshot(widget=None) -> str:
    """Encode visible content as PNG, marshaling worker calls to Kivy."""
    return _run_on_main_thread(_encoded_screenshot, widget)


def _pin_shortcut(script: str, label: str | None = None) -> None:
    from android_here import pin_shortcut as pin_android_shortcut

    shortcut_label = label or script.rstrip("/").rsplit("/", 1)[-1]
    pin_android_shortcut(script=script, label=shortcut_label)


def pin_shortcut(script: str, label: str | None = None) -> None:
    """Request an Android shortcut, marshaling worker calls to Kivy."""
    return _run_on_main_thread(_pin_shortcut, script, label)


__all__ = (
    "encoded_screenshot",
    "MainThreadBridgeError",
    "MainThreadTimeoutError",
    "pin_shortcut",
    "runtime_info",
    "save_screenshot",
    "snapshot_ui",
)
