from kivy.uix.settings import Settings

from ui_here.settings_here import SettingsHere


def test_build_settings_password_type_added():
    settings = SettingsHere()
    assert 'password' in settings._types
