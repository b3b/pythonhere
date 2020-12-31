"""Utilities for working with Kivy window."""
from base64 import b64encode
import os
from pathlib import Path
import time

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout


def reset_window_environment() -> BoxLayout:
    """Remove PythonHere app widgets and styles."""
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


def encoded_screenshot() -> str:
    """Return base64 encoded displayed image."""
    path = str(Path(f"screenshot_{time.time()}.png").resolve())
    Window.children[0].export_to_png(path)
    with open(path, "rb") as png_file:
        data = b64encode(png_file.read()).decode()
    os.remove(path)
    return data
