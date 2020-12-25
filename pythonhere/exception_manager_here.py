"""App exceptions manager."""
import asyncio
import traceback

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
        CodeInput:
            id: catched_exception_code_input_here
            size_hint: 1, 1
            text: root.message
            size_hint: 1, 1
        Button:
            size_hint_y: None
            height: '40sp'
            text: 'OK, continue'
            on_press: root.dismiss()
    """
    )


class ErrorMessageOnException(ExceptionHandler):
    """Handler that catches App exceptions, and show error message with details."""

    def handle_exception(self, exception):
        """Handle a exception."""
        if isinstance(exception, (asyncio.CancelledError, KeyboardInterrupt)):
            return ExceptionManager.RAISE

        load_exception_popup_style()
        Logger.exception("Unhandled Exception catched")
        message = UnhandledExceptionPopupHere(message=traceback.format_exc())

        message.open()

        def reset_cursor(_):
            message.ids.catched_exception_code_input_here.cursor = (0, 0)

        Clock.schedule_once(reset_cursor)
        return ExceptionManager.PASS


class UnhandledExceptionPopupHere(Popup):
    """Popup with details about exception."""

    message = StringProperty("")


def install_exception_handler():
    """Install `ErrorMessageOnException` exception handler."""
    ExceptionManager.add_handler(ErrorMessageOnException())
