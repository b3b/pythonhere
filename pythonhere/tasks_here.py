"""Durable sequential task execution for PythonHere.

TaskRunner provides persistent named runs with retries, progress inspection,
and at-least-once recovery after process interruption.

An optional setup callback can create runtime state once per worker session::

    def setup():
        return create_runtime()

    def execute_task(task, runtime):
        return runtime.process(task)

    runner.start(execute_task, setup=setup)

Without setup, the executor still receives a second argument, whose value is
``None``::

    def execute_task(task, context):
        return task["value"] * 2

    runner.start(execute_task)
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import shutil
import sys
import threading
import time
import traceback
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from persistqueue import SQLiteAckQueue
from persistqueue.exceptions import Empty

# pylint: disable=too-many-lines

__all__ = [
    "TaskRunner",
    "TaskRunnerError",
    "TaskRunExistsError",
    "TaskRunNotFoundError",
    "DuplicateTaskError",
    "TaskSubmissionError",
    "TaskRunnerAlreadyRunningError",
    "TaskRunnerBusyError",
    "TaskRunnerClosedError",
    "task_runs_directory",
]


log = logging.getLogger(__name__)

_SCHEMA_VERSION = 1
_RUN_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# persist-queue SQLiteAckQueue status values in 1.1.0.
# Keep these local rather than importing a private implementation class.
_PQ_INITED = "0"
_PQ_READY = "1"
_PQ_UNACK = "2"
_PQ_ACKED = "5"
_PQ_FAILED = "9"

_REGISTRY_LOCK = threading.RLock()
_INSTANCES: dict[str, TaskRunner] = {}

# Runs are exclusive process-wide by default so separate workloads cannot
# accidentally compete for a shared device or another constrained resource.
# Set exclusive=False when parallel independent runners are explicitly desired.
_EXECUTION_OWNER: dict[str, str] = {}


class TaskRunnerError(RuntimeError):
    """Base error for TaskRunner."""


class TaskRunExistsError(TaskRunnerError):
    """A run with this name already exists."""


class TaskRunNotFoundError(TaskRunnerError):
    """The requested run does not exist."""


class DuplicateTaskError(TaskRunnerError):
    """A task id already exists in the run."""


class TaskSubmissionError(TaskRunnerError):
    """Storage failed during submission; inspect the run before resubmitting."""

    def __init__(self, submitted_ids: list[str]):
        self.submitted_ids = submitted_ids
        super().__init__(
            f"Submission failed after {len(submitted_ids)} confirmed writes; "
            "inspect get(id) before resubmitting missing tasks"
        )


class TaskRunnerAlreadyRunningError(TaskRunnerError):
    """This runner already has an active worker."""


class TaskRunnerBusyError(TaskRunnerError):
    """Another exclusive TaskRunner is already executing."""


class TaskRunnerClosedError(TaskRunnerError):
    """Operation attempted on a closed runner."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def task_runs_directory() -> Path:
    """
    Return the default persistent TaskRunner directory.

    Override with PYTHONHERE_TASKS_DIR when needed. Android uses the current
    application's private files directory; desktop uses its user data directory.
    """
    configured = os.environ.get("PYTHONHERE_TASKS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    if sys.platform == "android" or "ANDROID_ARGUMENT" in os.environ:
        from android.storage import app_storage_path

        return Path(app_storage_path()) / "task-runs"
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home).expanduser() if data_home else Path.home() / ".local/share"
    return base / "pythonhere/task-runs"


def _plain_value(value: Any) -> Any:
    """Validate and snapshot portable values before writing or invoking user code."""

    def check(item):
        if item is None or isinstance(item, (bool, int, float, str)):
            return
        if isinstance(item, list):
            for child in item:
                check(child)
            return
        if isinstance(item, dict) and all(isinstance(key, str) for key in item):
            for child in item.values():
                check(child)
            return
        raise TypeError("Tasks and results must contain plain JSON-compatible values")

    check(value)
    return json.loads(json.dumps(value, allow_nan=False))


def _normalize_root(root: str | os.PathLike[str] | None) -> Path:
    if root is None:
        return task_runs_directory()
    return Path(root).expanduser().resolve()


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not _RUN_NAME_RE.fullmatch(name):
        raise ValueError(r"TaskRunner name must match [A-Za-z0-9][A-Za-z0-9._-]*")
    if name in {".", ".."}:
        raise ValueError("Invalid TaskRunner name")
    return name


def _run_path(name: str, root: Path) -> Path:
    return root / _validate_name(name)


def _registry_key(path: Path) -> str:
    return str(path.resolve())


def _atomic_write_json(
    path: Path, value: Mapping[str, Any] | list[dict[str, Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}")

    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(
                value,
                f,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
    except FileNotFoundError as exc:
        raise TaskRunNotFoundError(f"Task run metadata not found: {path}") from exc

    if not isinstance(value, dict):
        raise TaskRunnerError(f"Invalid TaskRunner metadata: {path}")

    return value


def _status_name(status: Any) -> str:
    status = str(status)

    if status in {_PQ_INITED, _PQ_READY}:
        return "pending"
    if status == _PQ_UNACK:
        return "running"
    if status == _PQ_ACKED:
        return "done"
    if status == _PQ_FAILED:
        return "failed"

    return f"unknown:{status}"


class TaskRunner:
    """
    Durable single-worker task runner.

    Use create() and open() instead of constructing this class directly.

    A run stores each task, its attempt history, result/error information, and
    queue status on disk. SQLiteAckQueue provides durable acknowledgement and
    recovery of tasks that were in-flight when the process died.
    """

    def __init__(
        self,
        *,
        name: str,
        root: Path,
        metadata: dict[str, Any],
        auto_resume: bool,
    ) -> None:
        self.name = name
        self.root = root
        self.path = _run_path(name, root)
        self._meta_path = self.path / "meta.json"
        self._queue_path = self.path / "queue"

        self.max_attempts = int(metadata["max_attempts"])
        self.exclusive = bool(metadata.get("exclusive", True))
        self._user_metadata = copy.deepcopy(metadata.get("metadata") or {})

        self._lock = threading.RLock()
        self._pause_requested = threading.Event()
        self._thread: threading.Thread | None = None
        self._current_task_id: str | None = None
        self._current_pqid: int | None = None
        self._closed = False
        self._worker_error: dict[str, Any] | None = None

        self._state = str(metadata.get("state", "idle"))
        self._created_at = str(metadata.get("created_at", _utc_now()))

        self.path.mkdir(parents=True, exist_ok=True)

        self._queue = SQLiteAckQueue(
            str(self._queue_path),
            auto_resume=auto_resume,
            multithreading=True,
        )

        # There are two small commit windows:
        #
        # 1. result persisted, process dies before ack()
        # 2. final error persisted, process dies before ack_failed()
        #
        # auto_resume makes both rows READY. Repair their queue status from the
        # durable record so already committed work is not needlessly rerun.
        self._recover_committed_records()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def create(  # pylint: disable=too-many-arguments
        cls,
        name: str,
        *,
        max_attempts: int = 3,
        metadata: Mapping[str, Any] | None = None,
        root: str | os.PathLike[str] | None = None,
        exclusive: bool = True,
    ) -> TaskRunner:
        """
        Create a new durable named run.

        Raises TaskRunExistsError when the name already exists.
        """
        name = _validate_name(name)
        root_path = _normalize_root(root)
        path = _run_path(name, root_path)
        key = _registry_key(path)

        if (
            not isinstance(max_attempts, int)
            or isinstance(max_attempts, bool)
            or max_attempts < 1
        ):
            raise ValueError("max_attempts must be a positive integer")

        # Use the same portable value contract for user metadata.
        user_metadata = _plain_value(dict(metadata or {}))
        with _REGISTRY_LOCK:
            if key in _INSTANCES or path.exists():
                raise TaskRunExistsError(f"Task run {name!r} already exists")

            path.mkdir(parents=True, exist_ok=False)

            created_at = _utc_now()
            initial_meta = {
                "schema_version": _SCHEMA_VERSION,
                "name": name,
                "created_at": created_at,
                "updated_at": created_at,
                "max_attempts": int(max_attempts),
                "exclusive": bool(exclusive),
                "state": "idle",
                "metadata": user_metadata,
                "summary": {
                    "total": 0,
                    "pending": 0,
                    "running": 0,
                    "completed": 0,
                    "failed": 0,
                    "progress": 0.0,
                },
                "worker_error": None,
            }

            try:
                _atomic_write_json(path / "meta.json", initial_meta)
                runner = cls(
                    name=name,
                    root=root_path,
                    metadata=initial_meta,
                    auto_resume=False,
                )
            except Exception:
                shutil.rmtree(path, ignore_errors=True)
                raise

            _INSTANCES[key] = runner

        runner._refresh_meta(state="idle")
        return runner

    @classmethod
    def open(
        cls,
        name: str,
        *,
        root: str | os.PathLike[str] | None = None,
    ) -> TaskRunner:
        """
        Open an existing run.

        If this Python process already has the run open, the existing object is
        returned. This is important: creating a second SQLiteAckQueue with
        auto_resume=True while the first runner is actively executing could
        reset its in-flight row.
        """
        name = _validate_name(name)
        root_path = _normalize_root(root)
        path = _run_path(name, root_path)
        key = _registry_key(path)

        with _REGISTRY_LOCK:
            existing = _INSTANCES.get(key)
            if existing is not None and not existing._closed:
                return existing

            meta_path = path / "meta.json"
            if not meta_path.exists():
                raise TaskRunNotFoundError(f"Task run {name!r} does not exist")

            metadata = _read_json(meta_path)

            if metadata.get("schema_version") != _SCHEMA_VERSION:
                raise TaskRunnerError(
                    f"Unsupported TaskRunner schema version: "
                    f"{metadata.get('schema_version')!r}"
                )

            if metadata.get("name") != name:
                raise TaskRunnerError(
                    f"TaskRunner metadata name mismatch in {meta_path}"
                )

            runner = cls(
                name=name,
                root=root_path,
                metadata=metadata,
                auto_resume=True,
            )
            _INSTANCES[key] = runner

        counts = runner._counts()
        previous_state = str(metadata.get("state", "idle"))

        if counts["total"] and (
            counts["completed"] + counts["failed"] == counts["total"]
        ):
            state = "completed"
        elif previous_state == "paused":
            state = "paused"
        elif previous_state == "idle":
            state = "idle"
        else:
            # A previous process said it was running (or was already marked
            # interrupted), but this process has no worker for it.
            state = "interrupted"

        runner._refresh_meta(state=state)
        return runner

    @classmethod
    def list(
        cls,
        *,
        root: str | os.PathLike[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        List persisted runs without reopening their queues.

        Reading meta.json rather than constructing SQLiteAckQueue instances is
        intentional: list() must never trigger auto-resume on a live run.
        """
        root_path = _normalize_root(root)
        if not root_path.exists():
            return []

        result: list[dict[str, Any]] = []

        for path in root_path.iterdir():
            if not path.is_dir():
                continue

            meta_path = path / "meta.json"
            if not meta_path.is_file():
                continue

            try:
                meta = _read_json(meta_path)
            except Exception:
                log.exception(
                    "TaskRunner: could not read metadata from %s",
                    meta_path,
                )
                continue

            key = _registry_key(path)
            with _REGISTRY_LOCK:
                live = _INSTANCES.get(key)

            if live is not None and not live._closed:
                try:
                    result.append(live.status())
                    continue
                except Exception:
                    log.exception(
                        "TaskRunner: could not inspect live run %s",
                        path.name,
                    )

            summary = dict(meta.get("summary") or {})
            state = str(meta.get("state", "idle"))

            # Active states in persisted metadata cannot still be active in
            # this process if no registered live instance exists.
            if state in {"running", "setting_up"}:
                state = "interrupted"

            result.append(
                {
                    "name": meta.get("name", path.name),
                    "state": state,
                    "max_attempts": meta.get("max_attempts"),
                    "exclusive": meta.get("exclusive", True),
                    "created_at": meta.get("created_at"),
                    "updated_at": meta.get("updated_at"),
                    "metadata": copy.deepcopy(meta.get("metadata") or {}),
                    **summary,
                }
            )

        result.sort(
            key=lambda item: str(item.get("updated_at") or ""),
            reverse=True,
        )
        return result

    def close(self) -> None:
        """
        Close local SQLite resources.

        A running worker cannot be closed. Closing does not delete the run.
        """
        with self._lock:
            self._ensure_open()
            if self.is_running():
                raise TaskRunnerAlreadyRunningError("Cannot close a running TaskRunner")

            self._queue.close()
            self._closed = True

        key = _registry_key(self.path)
        with _REGISTRY_LOCK:
            if _INSTANCES.get(key) is self:
                _INSTANCES.pop(key, None)

    def delete(self) -> None:
        """
        Permanently delete this run and all stored tasks/results.

        The runner must not be active.
        """
        with self._lock:
            self._ensure_open()
            if self.is_running():
                raise TaskRunnerAlreadyRunningError(
                    "Cannot delete a running TaskRunner"
                )

        path = self.path
        self.close()
        shutil.rmtree(path)

    def __enter__(self) -> TaskRunner:
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Submission and execution
    # ------------------------------------------------------------------

    def add(self, tasks: Iterable[Mapping[str, Any]]) -> int:
        """
        Durably add tasks.

        Each task must be a mapping containing a non-empty string ``id``.
        Duplicate ids are rejected across the whole run.

        Validation failures write nothing. Storage failures may commit a prefix;
        TaskSubmissionError reports confirmed IDs. Inspect get(id) before retrying.
        Returns the number of tasks added.
        """
        with self._lock:
            self._ensure_open()

            if self.is_running():
                raise TaskRunnerAlreadyRunningError(
                    "Cannot add tasks while the runner is active"
                )

            existing_ids = {
                record["task_id"]
                for record in self._all_queue_records()
                if isinstance(record.get("task_id"), str)
            }

            prepared: list[dict[str, Any]] = []
            submitted_ids: set[str] = set()

            for original in tasks:
                if not isinstance(original, Mapping):
                    raise TypeError(
                        f"Task must be a mapping, got {type(original).__name__}"
                    )

                task = _plain_value(dict(original))
                task_id = task.get("id")

                if not isinstance(task_id, str) or not task_id:
                    raise ValueError("Each task must contain a non-empty string 'id'")

                if task_id in existing_ids or task_id in submitted_ids:
                    raise DuplicateTaskError(f"Duplicate task id: {task_id!r}")

                prepared.append(
                    {
                        "schema_version": _SCHEMA_VERSION,
                        "task_id": task_id,
                        "task": task,
                        "created_at": _utc_now(),
                        "attempts": [],
                        "result_present": False,
                        "result": None,
                        "completed_at": None,
                    }
                )
                submitted_ids.add(task_id)

            confirmed_ids = []
            try:
                for record in prepared:
                    self._queue.put(record)
                    confirmed_ids.append(record["task_id"])

                if prepared:
                    self._pause_requested.clear()
                    self._worker_error = None
                    self._refresh_meta(state="idle")
            except Exception as exc:
                raise TaskSubmissionError(confirmed_ids) from exc

            return len(prepared)

    def start(
        self,
        execute: Callable[[dict[str, Any], Any], Any],
        *,
        setup: Callable[[], Any] | None = None,
    ) -> TaskRunner:
        """
        Start/resume sequential execution in a daemon background thread.

        The method returns immediately.

        ``setup()``, when supplied, runs once in the worker thread before any
        task is claimed. Its return value is passed unchanged to every
        ``execute(task, context)`` call in that worker session. Without setup,
        context is ``None``. Executors must return plain JSON-compatible data.
        Executor and result-validation errors consume the max_attempts failure
        budget. Interrupted executions do not consume it. Retries run after
        later ready rows, wrapping to the beginning when needed.

        The runner does not retain or clean up context after the worker exits.
        Applications remain responsible for deterministic resource cleanup.
        """
        if not callable(execute):
            raise TypeError("execute must be callable")
        if setup is not None and not callable(setup):
            raise TypeError("setup must be callable or None")

        with self._lock:
            self._ensure_open()

            if self.is_running():
                raise TaskRunnerAlreadyRunningError(
                    f"Task run {self.name!r} is already running"
                )

            # Repair a stale unack row left by an unexpected worker-thread
            # failure in the same process, then repair any committed-but-not-
            # acked records.
            self._queue.resume_unack_tasks()
            self._recover_committed_records()

            counts = self._counts()
            if counts["pending"] == 0:
                state = "completed" if counts["total"] > 0 else "idle"
                self._refresh_meta(state=state)
                return self

            self._claim_execution()

            try:
                self._pause_requested.clear()
                self._worker_error = None
                self._current_task_id = None
                self._current_pqid = None
                initial_state = "setting_up" if setup is not None else "running"
                self._refresh_meta(state=initial_state)

                thread = threading.Thread(
                    target=self._run_loop,
                    args=(execute, setup),
                    name=f"TaskRunner[{self.name}]",
                    daemon=True,
                )
                self._thread = thread

                thread.start()
            except Exception:
                self._thread = None
                self._release_execution()
                self._state = "interrupted"
                try:
                    self._refresh_meta(state="interrupted")
                except Exception:
                    log.exception(
                        "TaskRunner %s: could not persist start failure",
                        self.name,
                    )
                raise

        return self

    def pause(self) -> None:
        """
        Request a graceful pause.

        The current execute() call is not cancelled. The worker finishes the
        current attempt and stops before taking another task.
        """
        with self._lock:
            self._ensure_open()

            if self.is_running():
                self._pause_requested.set()
            else:
                counts = self._counts()
                if counts["pending"] > 0:
                    self._refresh_meta(state="paused")

    def wait(self, timeout: float | None = None) -> bool:
        """
        Wait for the current worker thread.

        Returns True if it is no longer running, False on timeout.
        """
        with self._lock:
            self._ensure_open()
            thread = self._thread

        if thread is None:
            return True

        thread.join(timeout)
        return not thread.is_alive()

    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> dict[str, Any]:
        return copy.deepcopy(self._user_metadata)

    def status(self) -> dict[str, Any]:
        """Return a small plain dictionary suitable for ``%there get``."""
        with self._lock:
            self._ensure_open()

            counts = self._counts()

            if self.is_running():
                state = "setting_up" if self._state == "setting_up" else "running"
            elif (
                counts["total"] > 0
                and counts["completed"] + counts["failed"] == counts["total"]
            ):
                state = "completed"
            else:
                state = self._state
                if state in {"running", "setting_up"}:
                    state = "interrupted"

            return {
                "name": self.name,
                "state": state,
                **counts,
                "current": self._current_task_id,
                "pause_requested": self._pause_requested.is_set(),
                "max_attempts": self.max_attempts,
                "exclusive": self.exclusive,
                "created_at": self._created_at,
                "updated_at": self._meta_updated_at(),
                "metadata": copy.deepcopy(self._user_metadata),
                "worker_error": copy.deepcopy(self._worker_error),
                "path": str(self.path),
            }

    def results(self) -> list[dict[str, Any]]:
        """
        Return all task records in submission order.

        This intentionally includes pending/running/failed tasks so the caller
        can inspect a run before it is complete.
        """
        with self._lock:
            self._ensure_open()
            rows = sorted(self._queue.queue(), key=lambda row: row["id"])
            return [self._public_record(row) for row in rows]

    def export_results(self, path: str | os.PathLike[str]) -> Path:
        """Atomically save a results snapshot as UTF-8 JSON and return its path.

        Includes all task records in submission order, just like results().
        Relative paths use the current working directory (PythonHere's upload
        directory by default), for retrieval with ``%there download``.
        Parent directories are created and an existing file is replaced only
        after a successful write. Run with ``%%there --worker`` for large runs.

        This avoids a large ``%there get`` response, but still materializes the
        complete results snapshot in device memory.
        """
        snapshot = self.results()
        destination = Path(path)
        _atomic_write_json(destination, snapshot)
        return destination

    def failed(self) -> list[dict[str, Any]]:
        """Return permanently failed task records."""
        return [record for record in self.results() if record["status"] == "failed"]

    def get(self, task_id: str) -> dict[str, Any] | None:
        """Return one task record by logical id, or None if not found."""
        if not isinstance(task_id, str):
            raise TypeError("task_id must be a string")

        with self._lock:
            self._ensure_open()

            for row in self._queue.queue():
                data = row.get("data")
                if isinstance(data, dict) and data.get("task_id") == task_id:
                    return self._public_record(row)

        return None

    # ------------------------------------------------------------------
    # Worker internals
    # ------------------------------------------------------------------

    def _run_loop(  # noqa: PLR0912, PLR0915  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        self,
        execute: Callable[[dict[str, Any], Any], Any],
        setup: Callable[[], Any] | None,
    ) -> None:
        final_state = "interrupted"

        previous_id = None
        phase = "setup"
        try:
            context = setup() if setup is not None else None
            phase = "execution"

            if setup is not None:
                with self._lock:
                    self._refresh_meta(state="running")

            while True:
                with self._lock:
                    if self._pause_requested.is_set():
                        break
                    try:
                        item = self._queue.get(
                            block=False,
                            raw=True,
                            id=previous_id,
                            next_in_order=previous_id is not None,
                        )
                    except Empty:
                        final_state = "completed"
                        break
                    self._current_pqid = int(item["pqid"])

                pqid = int(item["pqid"])
                previous_id = pqid
                record = item["data"]

                if not isinstance(record, dict):
                    # This should never happen for a TaskRunner-created queue.
                    self._queue.ack_failed(id=pqid)
                    log.error(
                        "TaskRunner %s: invalid queue record %r",
                        self.name,
                        record,
                    )
                    continue

                task = record.get("task")
                task_id = record.get("task_id")

                if not isinstance(task, dict) or not isinstance(task_id, str):
                    self._queue.ack_failed(id=pqid)
                    log.error(
                        "TaskRunner %s: invalid task record pqid=%s",
                        self.name,
                        pqid,
                    )
                    continue

                attempt_number = len(record.get("attempts") or []) + 1
                attempt = {
                    "number": attempt_number,
                    "started_at": _utc_now(),
                    "finished_at": None,
                    "duration": None,
                    "error": None,
                }

                record.setdefault("attempts", []).append(attempt)

                with self._lock:
                    self._current_task_id = task_id
                    self._current_pqid = pqid
                    # Commit "attempt started" before entering arbitrary user
                    # code. A process kill from this point onward is visible
                    # during recovery.
                    self._queue.update({"pqid": pqid, "data": record})
                    self._refresh_meta(state="running")

                started = time.monotonic()
                log.info(
                    "TaskRunner %s: starting %s attempt %d/%d",
                    self.name,
                    task_id,
                    attempt_number,
                    self.max_attempts,
                )

                try:
                    result = _plain_value(execute(copy.deepcopy(task), context))
                except Exception as exc:
                    duration = time.monotonic() - started

                    with self._lock:
                        attempt["finished_at"] = _utc_now()
                        attempt["duration"] = duration
                        attempt["error"] = {
                            "type": type(exc).__name__,
                            "message": str(exc),
                            "traceback": traceback.format_exc(),
                        }

                        record["last_error"] = copy.deepcopy(attempt["error"])
                        self._queue.update({"pqid": pqid, "data": record})

                        failure_count = self._failure_count(record)

                        if failure_count >= self.max_attempts:
                            self._queue.ack_failed(id=pqid)
                            log.exception(
                                "TaskRunner %s: task %s failed "
                                "permanently after %d failures",
                                self.name,
                                task_id,
                                failure_count,
                            )
                        else:
                            self._queue.nack(id=pqid)
                            log.warning(
                                "TaskRunner %s: task %s failed "
                                "(failure %d/%d, execution attempt %d): %s",
                                self.name,
                                task_id,
                                failure_count,
                                self.max_attempts,
                                attempt_number,
                                exc,
                            )

                        self._current_task_id = None
                        self._current_pqid = None
                        self._refresh_meta(state="running")

                else:
                    duration = time.monotonic() - started

                    with self._lock:
                        attempt["finished_at"] = _utc_now()
                        attempt["duration"] = duration
                        record["result"] = result
                        record["result_present"] = True
                        record["completed_at"] = _utc_now()
                        record.pop("last_error", None)

                        # Commit result before ack. If the process dies in the
                        # tiny window before ack(), open() recognizes this
                        # durable completion and repairs the queue status.
                        self._queue.update({"pqid": pqid, "data": record})
                        self._queue.ack(id=pqid)

                        self._current_task_id = None
                        self._current_pqid = None
                        self._refresh_meta(state="running")

                    log.info(
                        "TaskRunner %s: completed %s in %.3fs",
                        self.name,
                        task_id,
                        duration,
                    )

            if self._pause_requested.is_set():
                final_state = "paused"

        except BaseException as exc:
            # Unexpected failures of runner machinery should not lose the
            # currently claimed queue item. Return it to READY when possible.
            if phase == "setup":
                log.exception("TaskRunner %s: setup failed", self.name)
            else:
                log.exception(
                    "TaskRunner %s: worker stopped unexpectedly",
                    self.name,
                )

            with self._lock:
                self._worker_error = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                    "time": _utc_now(),
                }

                if self._current_pqid is not None:
                    try:
                        self._queue.nack(id=self._current_pqid)
                    except Exception:
                        log.exception(
                            "TaskRunner %s: could not nack interrupted pqid=%s",
                            self.name,
                            self._current_pqid,
                        )

                self._current_task_id = None
                self._current_pqid = None

            final_state = "interrupted"

        finally:
            with self._lock:
                self._current_task_id = None
                self._current_pqid = None

                # If no runnable work is left, terminal status wins over
                # "paused".
                try:
                    counts = self._counts()
                    if (
                        counts["total"] > 0
                        and counts["completed"] + counts["failed"] == counts["total"]
                    ):
                        final_state = "completed"
                except Exception:
                    log.exception(
                        "TaskRunner %s: could not compute final status",
                        self.name,
                    )

                try:
                    self._refresh_meta(state=final_state)
                except Exception:
                    log.exception(
                        "TaskRunner %s: could not persist final metadata",
                        self.name,
                    )

            self._release_execution()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _recover_committed_records(self) -> None:
        """
        Repair READY rows whose result/final failure was already persisted.

        SQLiteAckQueue auto-resume intentionally turns old UNACK rows back to
        READY. Usually they should be rerun. The exception is when TaskRunner
        already committed a successful result or the final failed attempt and
        the old process died immediately before ack()/ack_failed().
        """
        for row in self._queue.queue():
            if str(row.get("status")) not in {
                _PQ_INITED,
                _PQ_READY,
            }:
                continue

            pqid = int(row["id"])
            record = row.get("data")

            if not isinstance(record, dict):
                continue

            if record.get("result_present") is True and record.get("completed_at"):
                self._queue.ack(id=pqid)
                continue

            attempts = record.get("attempts")
            if not isinstance(attempts, list) or not attempts:
                continue

            last_attempt = attempts[-1]
            if not isinstance(last_attempt, dict):
                continue

            # A process kill is an interrupted execution attempt, not an
            # executor failure. Preserve it in history, but do not consume the
            # max_attempts failure budget.
            if (
                last_attempt.get("started_at")
                and not last_attempt.get("finished_at")
                and last_attempt.get("error") is None
                and not last_attempt.get("interrupted_at")
            ):
                last_attempt["interrupted_at"] = _utc_now()
                last_attempt["interrupted"] = True
                self._queue.update({"pqid": pqid, "data": record})

            if self._failure_count(record) >= self.max_attempts:
                self._queue.ack_failed(id=pqid)

        # ack() and ack_failed() normally follow get(), which already removed
        # the item from qsize(). Recovered items were put back into READY by
        # auto-resume, so recalculate the public pending counter after repair.
        self._queue.resume_unack_tasks()

    @staticmethod
    def _failure_count(record: Mapping[str, Any]) -> int:
        attempts = record.get("attempts")
        if not isinstance(attempts, list):
            return 0

        return sum(
            1
            for attempt in attempts
            if isinstance(attempt, dict)
            and attempt.get("finished_at")
            and attempt.get("error") is not None
        )

    def _all_queue_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for row in self._queue.queue():
            data = row.get("data")
            if isinstance(data, dict):
                records.append(data)

        return records

    def _counts(self) -> dict[str, Any]:
        # Public count helpers do not deserialize prompts or results. qsize()
        # includes persist-queue's newly inserted and retry-ready rows.
        pending = self._queue.qsize()
        running = self._queue.unack_count()
        completed = self._queue.acked_count()
        failed = self._queue.ack_failed_count()

        total = pending + running + completed + failed
        terminal = completed + failed

        return {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "progress": (terminal / total) if total else 0.0,
        }

    def _public_record(
        self,
        row: Mapping[str, Any],
    ) -> dict[str, Any]:
        record = row.get("data")

        if not isinstance(record, dict):
            return {
                "id": None,
                "status": _status_name(row.get("status")),
                "task": None,
                "result": None,
                "attempt_count": 0,
                "attempts": [],
                "error": {
                    "type": "TaskRunnerRecordError",
                    "message": "Invalid persisted task record",
                },
            }

        attempts = copy.deepcopy(record.get("attempts") or [])

        durations = [
            attempt.get("duration")
            for attempt in attempts
            if isinstance(attempt, dict)
            and isinstance(attempt.get("duration"), (int, float))
        ]

        result_present = bool(record.get("result_present"))

        return {
            "id": record.get("task_id"),
            "status": _status_name(row.get("status")),
            "task": copy.deepcopy(record.get("task")),
            "result": (copy.deepcopy(record.get("result")) if result_present else None),
            "result_present": result_present,
            "attempt_count": len(attempts),
            "failure_count": self._failure_count(record),
            "attempts": attempts,
            "duration": durations[-1] if durations else None,
            "total_duration": sum(durations),
            "error": copy.deepcopy(record.get("last_error")),
            "created_at": record.get("created_at"),
            "completed_at": record.get("completed_at"),
        }

    def _refresh_meta(self, *, state: str | None = None) -> None:
        if state is not None:
            self._state = state

        now = _utc_now()
        counts = self._counts()

        meta = {
            "schema_version": _SCHEMA_VERSION,
            "name": self.name,
            "created_at": self._created_at,
            "updated_at": now,
            "max_attempts": self.max_attempts,
            "exclusive": self.exclusive,
            "state": self._state,
            "metadata": copy.deepcopy(self._user_metadata),
            "summary": counts,
            "worker_error": copy.deepcopy(self._worker_error),
        }

        _atomic_write_json(self._meta_path, meta)

    def _meta_updated_at(self) -> str | None:
        try:
            return _read_json(self._meta_path).get("updated_at")
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Process-wide execution ownership
    # ------------------------------------------------------------------

    def _claim_execution(self) -> None:
        if not self.exclusive:
            return

        key = _registry_key(self.path)

        with _REGISTRY_LOCK:
            owner = _EXECUTION_OWNER.get("path")
            if owner is not None and owner != key:
                owner_name = Path(owner).name
                raise TaskRunnerBusyError(
                    f"Another exclusive task run is active: {owner_name!r}"
                )

            _EXECUTION_OWNER["path"] = key

    def _release_execution(self) -> None:
        if not self.exclusive:
            return

        key = _registry_key(self.path)

        with _REGISTRY_LOCK:
            if _EXECUTION_OWNER.get("path") == key:
                _EXECUTION_OWNER.pop("path")

    def _ensure_open(self) -> None:
        if self._closed:
            raise TaskRunnerClosedError(f"Task run {self.name!r} is closed")
