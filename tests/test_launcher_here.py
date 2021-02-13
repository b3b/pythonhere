import pytest
from launcher_here import run_script, try_startup_script


def test_run_script(mocker, test_py_script):
    run_path = mocker.patch("runpy.run_path")
    run_script(test_py_script)
    run_path.assert_called_once()


def test_run_script_not_found(mocker):
    run_path = mocker.patch("runpy.run_path")
    with pytest.raises(Exception, match="Script not found"):
        run_script("not_exist.py")
    run_path.assert_not_called()


def test_try_startup_script_not_android(mocker):
    run_script = mocker.patch("launcher_here.run_script")
    try_startup_script()
    run_script.assert_not_called()


def test_try_startup_script(mocker, mocked_android_modules):
    mocker.patch("launcher_here.platform", "android")
    run_script = mocker.patch("launcher_here.run_script")

    try_startup_script()
    run_script.assert_called_once()


def test_try_startup_exception(mocker, mocked_android_modules):
    mocker.patch("launcher_here.platform", "android")
    logger_exception = mocker.patch("launcher_here.Logger.exception")
    run_script = mocker.patch("launcher_here.run_script",
                              side_effect=Exception("test"))

    with pytest.raises(Exception, match="test"):
        try_startup_script()

    run_script.assert_called_once()
    logger_exception.assert_called_once()


def test_try_startup_no_script(mocker, mocked_android_modules):
    mocker.patch("launcher_here.platform", "android")
    mocker.patch("android_here.get_startup_script", return_value=None)
    run_script = mocker.patch("launcher_here.run_script")

    try_startup_script()
    run_script.assert_not_called()
