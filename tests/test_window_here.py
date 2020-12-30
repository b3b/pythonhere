from base64 import b64decode
from window_here import encoded_screenshot, reset_window_environment


def test_builder_unload_file_called(app_instance, mocker):
    unload_file = mocker.patch("window_here.Builder.unload_file")
    reset_window_environment()
    assert unload_file.call_count > 0


def test_encoded_screenshot_png_returned(app_instance):
    data = b64decode(encoded_screenshot())
    assert list(data[:8]) == [137, 80, 78, 71, 13, 10, 26, 10]
