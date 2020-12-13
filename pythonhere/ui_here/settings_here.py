"""Settings panel widgets."""
from kivy.uix.label import Label
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module


class SettingTitleHere(Label):
    """A simple title label, used to organize the settings in sections."""

    title = Label.text
    panel = ObjectProperty(None)
