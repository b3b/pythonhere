"""Settings panel widgets."""
from typing import Any, Dict

from kivy.config import Config
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.label import Label
from kivy.uix.settings import Settings, SettingString


SETTINGS_HERE = """
[
    {
        "type": "title",
        "title": "%here server"
    },
    {
        "type": "string",
        "title": "Username",
        "desc": "Username to ask (THERE_USERNAME)",
        "section": "pythonhere",
        "key": "username"
    },
    {
        "type": "password",
        "title": "Password",
        "desc": "Password to ask (THERE_PASSWORD)",
        "section": "pythonhere",
        "key": "password"
    },
    {
        "type": "numeric",
        "title": "Port",
        "desc": "Server port number, to start on this device (THERE_PORT)",
        "section": "pythonhere",
        "key": "port"
    }
]
"""


class SettingTitleHere(Label):
    """A simple title label, used to organize the settings in sections."""

    title = Label.text
    panel = ObjectProperty(None)


class PasswordLabel(Label):
    """Label wit a hidden text."""


class SettingPassword(SettingString):
    """String setting with a hidden text."""

    def _create_popup(self, instance):
        """Create popup with a password input."""
        super()._create_popup(instance)
        self.textinput.password = True

    def add_widget(self, widget, *largs):  # pylint: disable=arguments-differ
        """Add widget, if it is not SettingsString Label."""
        if isinstance(widget, PasswordLabel) or not isinstance(widget, Label):
            super().add_widget(widget, *largs)


class SettingsHere(Settings):
    """Customized settings panel."""

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        # remove "Close" button
        self.interface.menu.remove_widget(self.interface.menu.ids.button)

        self.register_type("title", SettingTitleHere)
        self.register_type("password", SettingPassword)

        Config.setdefaults(
            "pythonhere", {"username": "here", "password": "", "port": 8022}
        )
        self.add_json_panel("PythonHere", Config, data=SETTINGS_HERE)
        self.add_kivy_panel()

    def get_pythonhere_config(self) -> Dict[str, Any]:
        """Extract server parts of the config."""
        return {
            "username": Config.get("pythonhere", "username"),
            "password": Config.get("pythonhere", "password"),
            "port": Config.getint("pythonhere", "port"),
        }
