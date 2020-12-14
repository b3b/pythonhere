"""Settings panel widgets."""
from kivy.config import Config
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.label import Label
from kivy.uix.settings import Settings, SettingString


SETTINGS_HERE = """
[
    {
        "type": "title",
        "title": "SSH server"
    },
    {
        "type": "string",
        "title": "Login",
        "desc": "SSH login",
        "section": "pythonhere",
        "key": "login"
    },
    {
        "type": "password",
        "title": "Password",
        "desc": "SSH password",
        "section": "pythonhere",
        "key": "password"
    },
    {
        "type": "numeric",
        "title": "Port",
        "desc": "SSH server port number",
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


def build_settings(settings: Settings):
    """Customize settings panel."""
    settings.register_type("title", SettingTitleHere)
    settings.register_type("password", SettingPassword)

    Config.setdefaults("pythonhere", {"username": "here", "password": "", "port": 8022})
    settings.add_json_panel("Python Here", Config, data=SETTINGS_HERE)
