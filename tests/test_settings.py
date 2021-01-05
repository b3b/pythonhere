from ui_here.settings_here import SettingsHere, ShowPolicySettingButton


def test_build_settings_password_type_added():
    settings = SettingsHere()
    assert 'password' in settings._types


def test_can_navigate_to_privacy_policy(mocker):
    webbrowser = mocker.patch("webbrowser.open")
    settings = SettingsHere()

    for uid in settings.interface.content.panels.keys():
        settings.interface.content.current_uid = uid
        for widget in settings.interface.content.walk():
            if isinstance(widget, ShowPolicySettingButton):
                widget.on_release()

    webbrowser.assert_called_once()
