"""Utilities for working with Kivy window."""

import time
from base64 import b64encode
from pathlib import Path

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout


def reset_window_environment() -> BoxLayout:
    """Remove PythonHere app widgets and styles."""
    # import Window inside function to avoid early loading of the app config
    from kivy.core.window import Window  # pylint: disable=import-outside-toplevel

    for widget in Window.children:
        widget.clear_widgets()
        Window.remove_widget(widget)
    for filename in Builder.files[1:]:
        Builder.unload_file(filename)
    root = BoxLayout(orientation="vertical")
    Window.add_widget(root)
    return root


def unload_app_kv_styles():
    """Unload previously applied KV rules."""
    for filename in [f for f in Builder.files if (f or "").isdigit()]:
        Builder.unload_file(filename)


def load_kv_string(code: str, clear_style: bool):
    """Insert given rules into the Kivy Language Builder."""
    from kivy.core.window import Window  # pylint: disable=import-outside-toplevel

    app = App.get_running_app()

    if clear_style:
        unload_app_kv_styles()

    # digits-only filename to distinguish from other styles
    filename = str(time.time()).replace(".", "")

    root = Builder.load_string(code, filename=filename)
    if root:
        for widget in Window.children:
            widget.clear_widgets()
            Window.remove_widget(widget)
        Window.add_widget(root)
        app.root = root
        app.update_ssh_server_namespace({"root": root})


def save_screenshot(path: str | Path, widget=None) -> str:
    """Save a widget, or the visible window content, as a PNG."""
    from kivy.core.window import Window  # pylint: disable=import-outside-toplevel

    if widget is None:
        if not Window.children:
            raise RuntimeError("PythonHere has no visible content to capture")
        widget = Window.children[0]

    destination = Path(path).expanduser().resolve()
    if not destination.parent.is_dir():
        raise FileNotFoundError(
            f"Screenshot directory does not exist: {destination.parent}"
        )
    widget.export_to_png(str(destination))
    return str(destination)


def encoded_screenshot(widget=None) -> str:
    """Return base64 encoded displayed image."""
    path = Path(f"screenshot_{time.time()}.png").resolve()
    try:
        save_screenshot(path, widget=widget)
        return b64encode(path.read_bytes()).decode()
    finally:
        path.unlink(missing_ok=True)
