"""Utilities for working with Kivy window."""
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
