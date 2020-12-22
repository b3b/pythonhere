from window_here import reset_window_environment


def test_builder_unload_file_called(app_instance, mocker):
    unload_file = mocker.patch("window_here.Builder.unload_file")
    reset_window_environment()
    assert unload_file.call_count > 0
