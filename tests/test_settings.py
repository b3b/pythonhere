from kivy.uix.settings import Settings

from ui_here.settings_here import build_settings


def test_build_settings_password_type_added():
    settings = Settings()
    build_settings(settings)
    assert 'password' in settings._types
