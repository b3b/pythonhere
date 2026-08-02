import json
import threading
from pathlib import Path

import pytest
import tools_here
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


class FakeClockNotRunningError(RuntimeError):
    pass


class FakeClockEvent:
    def __init__(self, clock, callback, clock_ended_callback):
        self.clock = clock
        self.callback = callback
        self.clock_ended_callback = clock_ended_callback
        self.cancelled = False

    def __call__(self):
        if not self.clock.running:
            raise FakeClockNotRunningError
        with self.clock.condition:
            self.clock.events.append(self)
            self.clock.condition.notify_all()

    def cancel(self):
        self.cancelled = True

    def run(self):
        if not self.cancelled:
            self.callback(0)

    def end_clock(self):
        if not self.cancelled:
            self.clock_ended_callback(self)


class FakeClock:
    def __init__(self, *, running=True):
        self.running = running
        self.events = []
        self.condition = threading.Condition()

    def create_lifecycle_aware_trigger(
        self,
        callback,
        clock_ended_callback,
        *,
        timeout,
        release_ref,
    ):
        assert timeout == 0
        assert release_ref is False
        return FakeClockEvent(self, callback, clock_ended_callback)

    def wait_for_events(self, count):
        with self.condition:
            assert self.condition.wait_for(lambda: len(self.events) >= count, 1)


def invoke_in_worker(call):
    outcome = {}

    def invoke():
        try:
            outcome["result"] = call()
        except BaseException as exc:
            outcome["error"] = exc

    thread = threading.Thread(target=invoke)
    thread.start()
    return thread, outcome


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


def test_main_thread_bridge_executes_directly_without_clock(mocker):
    clock_boundary = mocker.patch("tools_here._clock_boundary")

    result = tools_here._run_on_main_thread(lambda value: value + 1, 2)

    assert result == 3
    clock_boundary.assert_not_called()


def test_main_thread_bridge_returns_worker_result_from_main_thread(mocker):
    clock = FakeClock()
    mocker.patch(
        "tools_here._clock_boundary",
        return_value=(clock, FakeClockNotRunningError),
    )
    worker, outcome = invoke_in_worker(
        lambda: tools_here._run_on_main_thread(
            lambda: ("value", threading.current_thread()),
        )
    )
    clock.wait_for_events(1)

    clock.events[0].run()
    worker.join(1)

    assert not worker.is_alive()
    assert outcome == {"result": ("value", threading.main_thread())}


def test_main_thread_bridge_propagates_implementation_exception(mocker):
    clock = FakeClock()
    mocker.patch(
        "tools_here._clock_boundary",
        return_value=(clock, FakeClockNotRunningError),
    )
    expected = ValueError("implementation failed")

    def fail():
        raise expected

    worker, outcome = invoke_in_worker(lambda: tools_here._run_on_main_thread(fail))
    clock.wait_for_events(1)
    clock.events[0].run()
    worker.join(1)

    assert outcome == {"error": expected}


def test_main_thread_bridge_reports_clock_stopping_before_callback(mocker):
    clock = FakeClock()
    mocker.patch(
        "tools_here._clock_boundary",
        return_value=(clock, FakeClockNotRunningError),
    )
    worker, outcome = invoke_in_worker(
        lambda: tools_here._run_on_main_thread(lambda: None)
    )
    clock.wait_for_events(1)

    clock.events[0].end_clock()
    worker.join(1)

    assert isinstance(outcome["error"], tools_here.MainThreadBridgeError)
    assert "Clock stopped" in str(outcome["error"])


def test_main_thread_bridge_reports_clock_already_stopped(mocker):
    clock = FakeClock(running=False)
    mocker.patch(
        "tools_here._clock_boundary",
        return_value=(clock, FakeClockNotRunningError),
    )
    worker, outcome = invoke_in_worker(
        lambda: tools_here._run_on_main_thread(lambda: None)
    )
    worker.join(1)

    assert isinstance(outcome["error"], tools_here.MainThreadBridgeError)
    assert "Clock is not running" in str(outcome["error"])


def test_main_thread_bridge_has_bounded_wait_and_cancels_pending_event(mocker):
    clock = FakeClock()
    mocker.patch(
        "tools_here._clock_boundary",
        return_value=(clock, FakeClockNotRunningError),
    )
    worker, outcome = invoke_in_worker(
        lambda: tools_here._run_on_main_thread(lambda: None, _timeout=0.01)
    )
    clock.wait_for_events(1)
    worker.join(1)

    assert not worker.is_alive()
    assert isinstance(outcome["error"], tools_here.MainThreadTimeoutError)
    assert "cancelled before it started" in str(outcome["error"])
    assert clock.events[0].cancelled is True


def test_main_thread_bridge_reports_when_timed_out_call_already_started(mocker):
    clock = FakeClock()
    mocker.patch(
        "tools_here._clock_boundary",
        return_value=(clock, FakeClockNotRunningError),
    )
    implementation_started = threading.Event()
    release_implementation = threading.Event()

    def stalled_operation():
        implementation_started.set()
        release_implementation.wait(1)

    worker, outcome = invoke_in_worker(
        lambda: tools_here._run_on_main_thread(stalled_operation, _timeout=0.01)
    )
    clock.wait_for_events(1)
    callback_thread = threading.Thread(target=clock.events[0].run)
    callback_thread.start()
    assert implementation_started.wait(1)
    worker.join(1)

    assert not worker.is_alive()
    assert isinstance(outcome["error"], tools_here.MainThreadTimeoutError)
    assert "started and may still complete" in str(outcome["error"])

    release_implementation.set()
    callback_thread.join(1)


def test_main_thread_bridge_keeps_concurrent_call_state_independent(mocker):
    clock = FakeClock()
    mocker.patch(
        "tools_here._clock_boundary",
        return_value=(clock, FakeClockNotRunningError),
    )

    def operation(value):
        if value == "bad":
            raise ValueError(value)
        return value

    first, first_outcome = invoke_in_worker(
        lambda: tools_here._run_on_main_thread(operation, "good")
    )
    second, second_outcome = invoke_in_worker(
        lambda: tools_here._run_on_main_thread(operation, "bad")
    )
    clock.wait_for_events(2)
    for event in clock.events:
        event.run()
    first.join(1)
    second.join(1)

    assert first_outcome == {"result": "good"}
    assert isinstance(second_outcome["error"], ValueError)
    assert str(second_outcome["error"]) == "bad"


@pytest.mark.parametrize(
    ("helper", "arguments"),
    [
        (snapshot_ui, ()),
        (runtime_info, ()),
        (save_screenshot, ()),
        (encoded_screenshot, ()),
        (pin_shortcut, ("scripts/demo.py",)),
    ],
)
def test_each_public_kivy_helper_uses_main_thread_bridge(
    mocker,
    helper,
    arguments,
):
    bridge = mocker.patch("tools_here._run_on_main_thread", return_value="result")

    assert helper(*arguments) == "result"
    bridge.assert_called_once()


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
