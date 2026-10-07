"""Tests for the durable sequential task runner."""

import json
import subprocess
import sys
import threading
from types import ModuleType

import pytest


@pytest.fixture
def module():
    import tasks_here as module

    yield module
    for runner in list(module._INSTANCES.values()):
        runner.pause()
        assert runner.wait(5)
        runner.close()


@pytest.fixture
def runner(module, tmp_path):
    return module.TaskRunner.create("test", root=tmp_path)


def finish(runner, execute, *, setup=None):
    runner.start(execute, setup=setup)
    assert runner.wait(5)
    assert runner.status()["worker_error"] is None


def test_export_results_snapshot(runner, tmp_path):
    runner.add([{"id": "a", "text": "Привет 🌍"}, {"id": "b"}])
    destination = tmp_path / "exports" / "results.json"
    assert runner.export_results(destination) == destination
    assert json.loads(destination.read_text(encoding="utf-8")) == runner.results()
    assert "Привет 🌍" in destination.read_text(encoding="utf-8")

    finish(runner, lambda task, context: task["id"])
    runner.export_results(str(destination))
    records = json.loads(destination.read_text(encoding="utf-8"))
    assert [record["result"] for record in records] == ["a", "b"]
    assert all(record["status"] == "done" for record in records)


def test_export_results_empty(runner, tmp_path):
    destination = runner.export_results(tmp_path / "empty.json")
    assert json.loads(destination.read_text(encoding="utf-8")) == []


def test_export_results_write_failure_preserves_file(runner, tmp_path, monkeypatch):
    destination = tmp_path / "results.json"
    destination.write_text("previous export", encoding="utf-8")

    def fail_dump(value, stream, **kwargs):
        stream.write("partial")
        raise OSError("disk full")

    monkeypatch.setattr(json, "dump", fail_dump)
    with pytest.raises(OSError, match="disk full"):
        runner.export_results(destination)
    assert destination.read_text(encoding="utf-8") == "previous export"
    assert list(tmp_path.glob(".results.json.tmp-*")) == []


def test_retry_order_and_reopen(module, runner, tmp_path):
    runner.add([{"id": "a"}, {"id": "b"}])
    calls = []

    def execute(task, context):
        assert context is None
        calls.append(task["id"])
        if task["id"] == "a" and calls.count("a") == 1:
            raise ValueError("temporary")
        return task["id"]

    finish(runner, execute)
    assert calls == ["a", "b", "a"]
    runner.close()
    reopened = module.TaskRunner.open("test", root=tmp_path)
    assert reopened.status()["completed"] == 2
    assert reopened.get("a")["failure_count"] == 1
    assert [r["result"] for r in reopened.results()] == ["a", "b"]


def test_invalid_result_and_mutated_input_do_not_stop_run(runner):
    runner.add([{"id": "bad"}, {"id": "good"}])

    def execute(task, context):
        assert context is None
        if task["id"] == "bad":
            task["oops"] = lambda: None
            return lambda: None
        return None

    finish(runner, execute)
    assert runner.get("bad")["failure_count"] == 3
    assert runner.get("bad")["task"] == {"id": "bad"}
    assert runner.get("bad")["status"] == "failed"
    assert runner.get("good")["result_present"] is True
    assert runner.status()["state"] == "completed"


@pytest.mark.parametrize(
    "bad",
    [
        {"id": "b", "value": lambda: None},
        {"id": "a"},
        {"value": 1},
        {"id": "b", "value": float("nan")},
    ],
)
def test_batch_validation_writes_nothing(runner, bad):
    with pytest.raises((TypeError, ValueError, RuntimeError)):
        runner.add([{"id": "a"}, bad])
    assert runner.status()["total"] == 0


def test_storage_failure_reports_partial_submission(module, runner, monkeypatch):
    put = runner._queue.put

    def broken_put(record):
        if record["task_id"] == "b":
            raise OSError("disk full")
        return put(record)

    with monkeypatch.context() as patch:
        patch.setattr(runner._queue, "put", broken_put)
        with pytest.raises(module.TaskSubmissionError) as exc:
            runner.add([{"id": "a"}, {"id": "b"}])
    assert exc.value.submitted_ids == ["a"]
    assert runner.get("a") is not None
    assert runner.get("b") is None
    runner.add([{"id": "b"}])
    finish(runner, lambda task, context: task["id"])
    assert runner.status()["completed"] == 2


def test_counts_do_not_load_payloads(runner, monkeypatch):
    runner.add([{"id": "a"}])
    runner.start(lambda task, context: "ok")
    assert runner.wait(5)

    def forbidden():
        pytest.fail("status deserialized queue payloads")

    monkeypatch.setattr(runner._queue, "queue", forbidden)
    assert runner.status()["completed"] == 1
    runner._refresh_meta()


def test_pending_count_uses_public_queue_size(runner, monkeypatch):
    runner.add([{"id": "a"}])
    monkeypatch.setattr(runner._queue, "qsize", lambda: 7)

    def forbidden():
        pytest.fail("pending count used ready_count instead of qsize")

    monkeypatch.setattr(runner._queue, "ready_count", forbidden)
    assert runner.status()["pending"] == 7


def test_results_are_sorted_by_queue_id(runner, monkeypatch):
    runner.add([{"id": "a"}, {"id": "b"}, {"id": "c"}])
    queue = runner._queue.queue
    monkeypatch.setattr(runner._queue, "queue", lambda: list(reversed(queue())))
    assert [record["id"] for record in runner.results()] == ["a", "b", "c"]


def test_start_failure_releases_execution(module, runner, tmp_path, monkeypatch):
    runner.add([{"id": "a"}])
    other = module.TaskRunner.create("other", root=tmp_path)
    other.add([{"id": "b"}])

    def broken_meta(**kwargs):
        raise OSError("disk full")

    with monkeypatch.context() as patch:
        patch.setattr(runner, "_refresh_meta", broken_meta)
        with pytest.raises(OSError):
            runner.start(lambda task, context: None)
    finish(other, lambda task, context: "ok")
    finish(runner, lambda task, context: "ok")


def test_pause_and_same_process_open(module, runner, tmp_path):
    entered = threading.Event()
    release = threading.Event()
    runner.add([{"id": "a"}, {"id": "b"}])

    def execute(task, context):
        assert context is None
        entered.set()
        assert release.wait(5)
        return task["id"]

    runner.start(execute)
    try:
        assert entered.wait(5)
        assert module.TaskRunner.open("test", root=tmp_path) is runner
        runner.pause()
    finally:
        release.set()
    assert runner.wait(5)
    assert runner.status()["state"] == "paused"
    assert runner.get("b")["attempt_count"] == 0
    finish(runner, lambda task, context: task["id"])


def test_setup_context_is_shared_unvalidated_and_on_worker_thread(runner):
    runner.add([{"id": "a"}, {"id": "b"}])
    setup_threads = []
    execute_threads = []
    contexts = []
    setup_calls = []
    lock = threading.Lock()

    def setup():
        setup_calls.append(True)
        setup_threads.append(threading.get_ident())
        return {"lock": lock, "callable": lambda: 42}

    def execute(task, context):
        contexts.append(context)
        execute_threads.append(threading.get_ident())
        assert context["lock"] is lock
        assert context["callable"]() == 42
        return task["id"]

    finish(runner, execute, setup=setup)

    assert len(setup_calls) == 1
    assert setup_threads[0] != threading.main_thread().ident
    assert execute_threads == [setup_threads[0], setup_threads[0]]
    assert contexts[0] is contexts[1]


def test_context_survives_executor_retry(runner):
    runner.add([{"id": "a"}])
    contexts = []

    def execute(task, context):
        contexts.append(context)
        if len(contexts) == 1:
            raise RuntimeError("temporary")
        return task["id"]

    finish(runner, execute, setup=object)

    assert len(contexts) == 2
    assert contexts[0] is contexts[1]
    assert runner.get("a")["failure_count"] == 1


def test_setup_failure_preserves_tasks_and_releases_execution(
    module, runner, tmp_path, caplog
):
    runner.add([{"id": "a"}, {"id": "b"}])
    caplog.set_level("ERROR", logger=module.__name__)

    def fail_setup():
        raise RuntimeError("setup failed")

    runner.start(lambda task, context: task["id"], setup=fail_setup)
    assert runner.wait(5)

    status = runner.status()
    assert status["state"] == "interrupted"
    assert status["pending"] == 2
    assert status["worker_error"]["type"] == "RuntimeError"
    assert status["worker_error"]["message"] == "setup failed"
    assert all(record["attempt_count"] == 0 for record in runner.results())
    assert "TaskRunner test: setup failed" in caplog.messages

    other = module.TaskRunner.create("other", root=tmp_path)
    other.add([{"id": "other"}])
    finish(other, lambda task, context: task["id"])

    setup_calls = []

    def setup():
        setup_calls.append(True)
        return "ready"

    finish(runner, lambda task, context: context, setup=setup)
    assert len(setup_calls) == 1
    assert runner.status()["worker_error"] is None
    assert [record["result"] for record in runner.results()] == ["ready", "ready"]


def test_pause_during_setup_is_responsive_and_claims_no_task(module, runner, tmp_path):
    entered = threading.Event()
    release = threading.Event()
    contexts = []
    executor_calls = []
    runner.add([{"id": "a"}, {"id": "b"}])

    def setup():
        context = object()
        contexts.append(context)
        entered.set()
        assert release.wait(5)
        return context

    runner.start(lambda task, context: executor_calls.append(task["id"]), setup=setup)
    try:
        assert entered.wait(5)
        assert module.TaskRunner.open("test", root=tmp_path) is runner
        status = runner.status()
        assert status["state"] == "setting_up"
        assert status["current"] is None
        assert all(record["attempt_count"] == 0 for record in runner.results())
        assert runner.wait(0.01) is False

        other = module.TaskRunner.create("other", root=tmp_path)
        other.add([{"id": "other"}])
        with pytest.raises(module.TaskRunnerBusyError):
            other.start(lambda task, context: None)

        runner.pause()
    finally:
        release.set()

    assert runner.wait(5)
    assert runner.status()["state"] == "paused"
    assert executor_calls == []
    assert all(record["attempt_count"] == 0 for record in runner.results())

    finish(
        runner,
        lambda task, context: task["id"],
        setup=lambda: contexts.append(object()) or contexts[-1],
    )
    assert len(contexts) == 2
    assert contexts[0] is not contexts[1]


def test_setup_status_transitions_to_running_before_task(runner):
    setup_entered = threading.Event()
    release_setup = threading.Event()
    execute_entered = threading.Event()
    release_execute = threading.Event()
    runner.add([{"id": "a"}, {"id": "b"}])

    def setup():
        setup_entered.set()
        assert release_setup.wait(5)
        return object()

    def execute(task, context):
        execute_entered.set()
        assert release_execute.wait(5)
        return task["id"]

    runner.start(execute, setup=setup)
    try:
        assert setup_entered.wait(5)
        setting_up = runner.status()
        assert setting_up["state"] == "setting_up"
        assert setting_up["pending"] == 2
        assert setting_up["running"] == 0
        assert setting_up["current"] is None

        release_setup.set()
        assert execute_entered.wait(5)
        running = runner.status()
        assert running["state"] == "running"
        assert running["running"] == 1
        assert running["current"] == "a"
    finally:
        release_setup.set()
        release_execute.set()

    assert runner.wait(5)
    assert runner.status()["state"] == "completed"


def test_no_setup_goes_directly_to_running(runner):
    entered = threading.Event()
    release = threading.Event()
    runner.add([{"id": "a"}])

    def execute(task, context):
        assert context is None
        entered.set()
        assert release.wait(5)
        return task["id"]

    runner.start(execute)
    try:
        assert entered.wait(5)
        assert runner.status()["state"] == "running"
    finally:
        release.set()

    assert runner.wait(5)


def test_setup_failure_takes_precedence_over_pause(runner):
    entered = threading.Event()
    release = threading.Event()
    runner.add([{"id": "a"}])

    def setup():
        entered.set()
        assert release.wait(5)
        raise RuntimeError("failed after pause")

    runner.start(lambda task, context: None, setup=setup)
    try:
        assert entered.wait(5)
        assert runner.status()["state"] == "setting_up"
        runner.pause()
    finally:
        release.set()

    assert runner.wait(5)
    status = runner.status()
    assert status["state"] == "interrupted"
    assert status["worker_error"]["message"] == "failed after pause"
    assert runner.get("a")["attempt_count"] == 0


def test_no_work_and_rejected_starts_do_not_call_setup(module, tmp_path):
    setup_calls = []

    def setup():
        setup_calls.append(True)

    empty = module.TaskRunner.create("empty", root=tmp_path)
    empty.start(lambda task, context: None, setup=setup)
    assert empty.status()["state"] == "idle"

    completed = module.TaskRunner.create("completed", root=tmp_path)
    completed.add([{"id": "a"}])
    finish(completed, lambda task, context: None)
    completed.start(lambda task, context: None, setup=setup)
    assert completed.status()["state"] == "completed"

    active = module.TaskRunner.create("active", root=tmp_path)
    active.add([{"id": "a"}])
    entered = threading.Event()
    release = threading.Event()

    def blocking_setup():
        entered.set()
        assert release.wait(5)

    active.start(lambda task, context: None, setup=blocking_setup)
    try:
        assert entered.wait(5)
        with pytest.raises(module.TaskRunnerAlreadyRunningError):
            active.start(lambda task, context: None, setup=setup)

        blocked = module.TaskRunner.create("blocked", root=tmp_path)
        blocked.add([{"id": "a"}])
        with pytest.raises(module.TaskRunnerBusyError):
            blocked.start(lambda task, context: None, setup=setup)
    finally:
        active.pause()
        release.set()
    assert active.wait(5)

    closed = module.TaskRunner.create("closed", root=tmp_path)
    closed.add([{"id": "a"}])
    closed.close()
    with pytest.raises(module.TaskRunnerClosedError):
        closed.start(lambda task, context: None, setup=setup)

    assert setup_calls == []


def test_callback_validation_and_falsey_setup(module, runner, tmp_path):
    runner.add([{"id": "a"}])
    before = runner.results()

    with pytest.raises(TypeError, match="execute must be callable"):
        runner.start(None)
    with pytest.raises(TypeError, match="setup must be callable or None"):
        runner.start(lambda task, context: None, setup=object())

    assert runner.results() == before
    other = module.TaskRunner.create("other", root=tmp_path)
    other.add([{"id": "b"}])
    finish(other, lambda task, context: None)

    class FalseySetup:
        def __init__(self):
            self.calls = 0

        def __bool__(self):
            return False

        def __call__(self):
            self.calls += 1

    setup = FalseySetup()
    contexts = []
    finish(
        runner,
        lambda task, context: contexts.append(context),
        setup=setup,
    )
    assert setup.calls == 1
    assert contexts == [None]


def test_setup_failure_preserves_partially_completed_run(module, tmp_path):
    runner = module.TaskRunner.create("mixed", root=tmp_path, max_attempts=1)
    runner.add([{"id": "a"}, {"id": "b"}, {"id": "c"}])

    def execute(task, context):
        if task["id"] == "b":
            runner.pause()
            raise ValueError("permanent")
        return task["id"]

    finish(runner, execute)
    assert [record["status"] for record in runner.results()] == [
        "done",
        "failed",
        "pending",
    ]
    before = runner.results()

    def fail_setup():
        raise RuntimeError("cannot initialize")

    runner.start(lambda task, context: task["id"], setup=fail_setup)
    assert runner.wait(5)
    assert runner.results() == before
    assert runner.status()["state"] == "interrupted"

    calls = []
    finish(
        runner,
        lambda task, context: calls.append(task["id"]) or task["id"],
        setup=object,
    )
    assert calls == ["c"]
    assert runner.status()["worker_error"] is None


@pytest.mark.parametrize("point", ["execute", "ack", "ack_failed"])
def test_abrupt_process_death(module, tmp_path, point):
    code = """import sys, os
from pythonhere.tasks_here import TaskRunner as T
r = T.create("crash", root=sys.argv[1], max_attempts=1)
r.add([{"id":"a"}, {"id":"b"}, {"id":"c"}])
point = sys.argv[2]
if point != "execute":
    original = getattr(r._queue, point)
    def stop(*args, **kwargs):
        if r._current_task_id == "b":
            os._exit(17)
        return original(*args, **kwargs)
    setattr(r._queue, point, stop)
def execute(task, context):
    assert context == "child-context"
    if task["id"] == "b":
        if point == "execute": os._exit(17)
        if point == "ack_failed": raise ValueError("permanent")
    return task["id"]
r.start(execute, setup=lambda: "child-context")
r.wait(5)
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), point], timeout=10, check=False
    )
    assert child.returncode == 17
    runner = module.TaskRunner.open("crash", root=tmp_path)
    assert runner.get("a")["status"] == "done"
    expected = {"execute": "pending", "ack": "done", "ack_failed": "failed"}[point]
    assert runner.get("b")["status"] == expected
    expected_recovery = {
        "execute": {"pending": 2, "completed": 1, "failed": 0, "progress": 1 / 3},
        "ack": {"pending": 1, "completed": 2, "failed": 0, "progress": 2 / 3},
        "ack_failed": {
            "pending": 1,
            "completed": 1,
            "failed": 1,
            "progress": 2 / 3,
        },
    }[point]
    recovered_status = runner.status()
    assert recovered_status["total"] == 3
    assert recovered_status["running"] == 0
    assert recovered_status["state"] == "interrupted"
    for key, value in expected_recovery.items():
        assert recovered_status[key] == value
    calls = []

    def execute_recovered(task, context):
        assert context == "parent-context"
        calls.append(task["id"])
        return task["id"]

    finish(
        runner,
        execute_recovered,
        setup=lambda: "parent-context",
    )
    assert calls == (["b", "c"] if point == "execute" else ["c"])
    final_status = runner.status()
    assert final_status["total"] == 3
    assert final_status["pending"] == 0
    assert final_status["running"] == 0
    assert final_status["completed"] == (2 if point == "ack_failed" else 3)
    assert final_status["failed"] == (1 if point == "ack_failed" else 0)
    assert final_status["progress"] == 1.0
    assert final_status["state"] == "completed"
    if point == "execute":
        assert runner.get("b")["attempt_count"] == 2
        assert runner.get("b")["failure_count"] == 0
        assert runner.get("b")["attempts"][0]["interrupted"] is True


def test_storage_paths(module, tmp_path, monkeypatch):
    monkeypatch.delenv("PYTHONHERE_TASKS_DIR", raising=False)
    monkeypatch.delenv("ANDROID_ARGUMENT", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert module.task_runs_directory() == tmp_path / "pythonhere/task-runs"
    android = ModuleType("android")
    storage = ModuleType("android.storage")
    storage.app_storage_path = lambda: str(tmp_path / "actual-package")
    monkeypatch.setitem(sys.modules, "android", android)
    monkeypatch.setitem(sys.modules, "android.storage", storage)
    monkeypatch.setenv("ANDROID_ARGUMENT", "1")
    assert module.task_runs_directory() == tmp_path / "actual-package/task-runs"
    monkeypatch.setenv("PYTHONHERE_TASKS_DIR", str(tmp_path / "override"))
    assert module.task_runs_directory() == tmp_path / "override"


def test_stale_setting_up_state_is_interrupted(module, runner, tmp_path):
    runner.add([{"id": "a"}])
    runner._refresh_meta(state="setting_up")
    assert runner.status()["state"] == "interrupted"
    runner.close()

    listed = next(item for item in module.TaskRunner.list(root=tmp_path))
    assert listed["state"] == "interrupted"

    reopened = module.TaskRunner.open("test", root=tmp_path)
    assert reopened.status()["state"] == "interrupted"


def test_thread_start_failure_releases_execution(module, runner, tmp_path, monkeypatch):
    runner.add([{"id": "a"}])

    def broken_start(thread):
        raise RuntimeError("cannot start thread")

    with monkeypatch.context() as patch:
        patch.setattr(threading.Thread, "start", broken_start)
        with pytest.raises(RuntimeError):
            runner.start(lambda task, context: None, setup=object)
    assert runner.status()["state"] == "interrupted"
    assert module._read_json(runner._meta_path)["state"] == "interrupted"
    other = module.TaskRunner.create("other", root=tmp_path)
    other.add([{"id": "b"}])
    finish(other, lambda task, context: None)
    finish(runner, lambda task, context: None)


def test_result_storage_failure_is_recoverable(runner, monkeypatch):
    runner.add([{"id": "a"}, {"id": "b"}])
    update = runner._queue.update

    def broken_update(item, *args, **kwargs):
        if item["data"].get("result_present"):
            raise OSError("disk full")
        return update(item, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(runner._queue, "update", broken_update)
        runner.start(lambda task, context: "ok")
        assert runner.wait(5)
    assert runner.status()["state"] == "interrupted"
    assert runner.status()["worker_error"]["type"] == "OSError"
    assert runner.get("b")["attempt_count"] == 0
    finish(runner, lambda task, context: "ok")
    assert runner.status()["completed"] == 2
