"""Settings panel widgets."""
from typing import Any, Dict
import webbrowser

from kivy.app import App
from kivy.config import Config
from kivy.properties import (  # pylint: disable=no-name-in-module
    BooleanProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.settings import Settings, SettingString

from enum_here import ScreenName


SETTINGS_HERE = """
[
    {
        "type": "title",
        "title": "%here server settings"
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
    },
    {
        "type": "start_server_button"
    }
]
"""

SETTINGS_PRIVACY = """[
    {
        "type": "title",
        "title": "PythonHere is intended for use as-is with no warranty of any kind."
    },
    {
        "type": "show_policy_button"
    }
]
"""


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


class SettingButton(AnchorLayout):
    """Button for settings panel."""

    title = StringProperty("")
    panel = ObjectProperty(None)
    active = BooleanProperty(True)

    def on_release(self):
        """Handler for button `on_release` event."""
        ...


class StartServerSettingButton(SettingButton):
    """Button to start %here."""

    def on_release(self):
        """Start the server."""
        app = App.get_running_app()
        app.update_server_config_status()
        app.root.switch_screen(ScreenName.here)


class ShowPolicySettingButton(SettingButton):
    """Button to show privacy policy."""

    def on_release(self):
        """Show the policy."""
        webbrowser.open("https://herethere.me/privacy_policy.html")


class SettingsHere(Settings):
    """Customized settings panel."""

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        # remove "Close" button
        self.interface.menu.remove_widget(self.interface.menu.ids.button)
        self.register_type("password", SettingPassword)
        self.register_type("start_server_button", StartServerSettingButton)
        self.register_type("show_policy_button", ShowPolicySettingButton)

        Config.setdefaults(
            "pythonhere", {"username": "here", "password": "", "port": 8022}
        )
        self.add_json_panel("PythonHere", Config, data=SETTINGS_HERE)
        self.add_kivy_panel()
        self.add_json_panel("Privacy Policy", Config, data=SETTINGS_PRIVACY)

    def get_pythonhere_config(self) -> Dict[str, Any]:
        """Extract server parts of the config."""
        return {
            "username": Config.get("pythonhere", "username"),
            "password": Config.get("pythonhere", "password"),
            "port": Config.getint("pythonhere", "port"),
        }
