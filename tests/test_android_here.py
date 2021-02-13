import pytest


@pytest.mark.parametrize(
    "script", (None, "test.py"),
)
def test_restart_app(mocked_android_modules, app_instance, test_py_script, script):
    from android_here import restart_app
    restart_app(script)


def test_script_path_resolved(mocked_android_modules, app_instance, test_py_script):
    from android_here import resolve_script_path
    path = resolve_script_path("test.py")
    assert path.startswith("/") and path.endswith("test.py")


def test_absolute_script_path_resolved(mocked_android_modules, app_instance, test_py_script):
    from android_here import resolve_script_path
    assert resolve_script_path(test_py_script) == test_py_script


def test_pin_shortcut(mocker, mocked_android_modules, app_instance, test_py_script):
    from android_here import pin_shortcut
    pin_shortcut("test.py", "test label")
