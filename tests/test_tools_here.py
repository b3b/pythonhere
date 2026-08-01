import json
import threading
from pathlib import Path

import pytest
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from tools_here import (
    encoded_screenshot,
    pin_shortcut,
    runtime_info,
    save_screenshot,
    snapshot_ui,
)


def test_snapshot_ui_returns_flat_observable_widget_facts(app_instance):
    app_instance.root.clear_widgets()
    button = Button(text="Inspect me")
    app_instance.root.add_widget(button)
    app_instance.root.ids["inspect_button"] = button

    result = snapshot_ui(app_instance.root)

    assert result["widgets"] == [
        {
            "path": "0",
            "class": type(app_instance.root).__name__,
            "text": None,
            "disabled": False,
            "pos": [round(float(value), 2) for value in app_instance.root.pos],
            "size": [
                round(float(app_instance.root.width), 2),
                round(float(app_instance.root.height), 2),
            ],
            "child_count": 1,
        },
        {
            "path": "0/0",
            "class": "Button",
            "text": "Inspect me",
            "disabled": False,
            "pos": [round(float(value), 2) for value in button.pos],
            "size": [round(float(value), 2) for value in button.size],
            "child_count": 0,
        },
    ]
    assert result["widget_count"] == 2
    assert result["truncated"] is False
    json.dumps(result)


def test_snapshot_ui_reports_soft_widget_limit_truncation(app_instance):
    app_instance.root.add_widget(Button(text="One"))
    app_instance.root.add_widget(Button(text="Two"))

    result = snapshot_ui(app_instance.root, max_widgets=1)

    assert result["widget_count"] == 1
    assert result["truncated"] is True


def test_snapshot_ui_reports_soft_depth_limit_truncation(app_instance):
    app_instance.root.clear_widgets()
    layout = BoxLayout()
    layout.add_widget(Button(text="Nested"))
    app_instance.root.add_widget(layout)

    result = snapshot_ui(app_instance.root, max_depth=0)

    assert result["widget_count"] == 1
    assert result["truncated"] is True
    assert result["widgets"][0]["child_count"] == 1


@pytest.mark.parametrize(
    ("arguments", "exception", "message"),
    [
        ({"max_depth": -1}, ValueError, "max_depth"),
        ({"max_depth": 49}, ValueError, "max_depth"),
        ({"max_depth": True}, TypeError, "max_depth"),
        ({"max_widgets": 0}, ValueError, "max_widgets"),
        ({"max_widgets": 501}, ValueError, "max_widgets"),
        ({"max_widgets": 2.5}, TypeError, "max_widgets"),
    ],
)
def test_snapshot_ui_validates_limits(
    app_instance,
    arguments,
    exception,
    message,
):
    with pytest.raises(exception, match=message):
        snapshot_ui(app_instance.root, **arguments)


def test_snapshot_ui_marks_truncated_text(mocker, app_instance):
    mocker.patch("tools_here.MAX_UI_SNAPSHOT_TEXT", 8)
    app_instance.root.clear_widgets()
    app_instance.root.add_widget(Button(text="Long button text"))

    result = snapshot_ui(app_instance.root)

    button = result["widgets"][1]
    assert button["text"] == "Long ..."
    assert button["text_truncated"] is True


def test_snapshot_ui_tolerates_failing_text_property():
    class FailingTextWidget:
        children = ()
        disabled = False
        pos = (0, 0)
        size = (100, 100)

        @property
        def text(self):
            raise RuntimeError("custom text failed")

    result = snapshot_ui(FailingTextWidget())

    assert result["widgets"][0]["text"] is None
    assert result["widgets"][0]["text_unavailable"] is True


def test_snapshot_ui_normalizes_nonfinite_geometry(app_instance):
    app_instance.root.clear_widgets()
    button = Button(text="Geometry")
    app_instance.root.add_widget(button)
    button.pos = (float("nan"), float("inf"))

    result = snapshot_ui(app_instance.root)

    assert result["widgets"][1]["pos"] == [None, None]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "call",
    [
        lambda app, output: snapshot_ui(app.root),
        lambda app, output: runtime_info(app, app.root),
        lambda app, output: save_screenshot(output, app.root),
        lambda app, output: encoded_screenshot(app.root),
        lambda app, output: pin_shortcut("scripts/demo.py"),
    ],
)
def test_kivy_tools_reject_worker_threads(tmp_path, app_instance, call):
    errors = []

    def invoke():
        try:
            call(app_instance, tmp_path / "screen.png")
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=invoke)
    thread.start()
    thread.join()

    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert str(errors[0]) == "This PythonHere tool must run on Kivy's main thread"


def test_runtime_info_is_json_compatible(app_instance):
    result = runtime_info(app_instance, app_instance.root)

    assert result["app_class"] == type(app_instance).__name__
    assert result["root_class"] == type(app_instance.root).__name__
    assert result["window_size"] == [float(value) for value in Window.size]
    json.dumps(result)


def test_save_screenshot_absolute_path(tmp_path, app_instance):
    output = tmp_path / "screen.png"

    result = save_screenshot(output, app_instance.root)

    assert result == str(output)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_save_screenshot_relative_to_upload_dir(app_instance):
    output = Path(app_instance.upload_dir) / "screen.png"

    result = save_screenshot("screen.png", app_instance.root)

    assert result == str(output)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_save_screenshot_without_widget_uses_window_default(
    tmp_path, mocker, app_instance
):
    implementation = mocker.patch(
        "window_here.save_screenshot",
        return_value=str(tmp_path / "screen.png"),
    )

    result = save_screenshot(tmp_path / "screen.png")

    assert result == str(tmp_path / "screen.png")
    implementation.assert_called_once_with(tmp_path / "screen.png", widget=None)


def test_encoded_screenshot_without_widget_uses_window_default(mocker, app_instance):
    implementation = mocker.patch(
        "window_here.encoded_screenshot",
        return_value="encoded-png",
    )

    result = encoded_screenshot()

    assert result == "encoded-png"
    implementation.assert_called_once_with(widget=None)


def test_pin_shortcut_delegates_with_default_label(
    mocker, mocked_android_modules, app_instance
):
    implementation = mocker.patch("android_here.pin_shortcut")

    pin_shortcut("scripts/demo.py")

    implementation.assert_called_once_with(
        script="scripts/demo.py",
        label="demo.py",
    )
