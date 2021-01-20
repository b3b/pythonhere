"""App exceptions manager."""
import asyncio
import traceback
from typing import Optional

from kivy.base import (
    ExceptionHandler,
    ExceptionManager,
)
from kivy.clock import Clock
from kivy.properties import StringProperty  # pylint: disable=no-name-in-module
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.popup import Popup


def load_exception_popup_style():
    """Load KV rules for `UnhandledExceptionPopupHere`."""
    Builder.load_string(
        """<-UnhandledExceptionPopupHere>:
    title: "Unhandled Exception catched"
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 20
        Label:
            size_hint_y: None
            font_size: '18sp'
            height: '24sp'
            text: 'Exception details: '
        ScrollView:
            CodeInput:
                id: catched_exception_code_input_here
                text: root.message
                size_hint: 1, None
                height: self.minimum_height
        Button:
            size_hint_y: None
            height: '40sp'
            text: 'OK, continue'
            on_press: root.dismiss()
    """
    )


class ErrorMessageOnException(ExceptionHandler):
    """Handler that catches App exceptions, and show error message with details."""

    def handle_exception(self, exception) -> int:
        """Handle a exception."""
        Logger.exception("Unhandled Exception catched")
        if isinstance(exception, (asyncio.CancelledError, KeyboardInterrupt)):
            return ExceptionManager.RAISE
        show_exception_popup()
        return ExceptionManager.PASS


class UnhandledExceptionPopupHere(Popup):
    """Popup with details about exception."""

    message = StringProperty("")


def install_exception_handler():
    """Install `ErrorMessageOnException` exception handler."""
    ExceptionManager.add_handler(ErrorMessageOnException())


def show_exception_popup(exc: Optional[Exception] = None):
    """Show exception popup."""
    load_exception_popup_style()
    if exc:
        message = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        message = traceback.format_exc()

    popup = UnhandledExceptionPopupHere(message=message)

    popup.open()

    def reset_cursor(_):
        popup.ids.catched_exception_code_input_here.cursor = (0, 0)

    Clock.schedule_once(reset_cursor)
