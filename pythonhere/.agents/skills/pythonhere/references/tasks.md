# Durable task runs

Use `TaskRunner` for sequential work that must continue after the client
disconnects, retain progress across a PythonHere restart, or retry individual
items.

## Start a run

```python
from tasks_here import TaskRunner

runner = TaskRunner.create("data-import", max_attempts=3)
runner.add([
    {"id": "part-1", "path": "one.json"},
    {"id": "part-2", "path": "two.json"},
])
runner.start(execute_task)
```

Tasks and results must contain plain JSON-compatible values. Every task needs a
unique nonempty string `id`. `start()` returns promptly and processes one task
at a time. Preserve the runner in a named global when later commands need it.

Inspect `runner.status()`, `runner.results()`, `runner.get(id)`, or
`runner.failed()` through normal `there get` calls. `pause()` finishes the
current item and stops before claiming another.

## Wait and inspect the outcome

After starting the runner, wait in bounded intervals through the CLI:

```bash
there --json --timeout 60 get --worker \
  "{'stopped': runner.wait(timeout=50), 'status': runner.status()}"
```

Here, `--worker` keeps the wait off the app's event loop.
Keep the CLI timeout longer than the wait timeout to allow time for connection
and response. If `stopped` is `false`, tasks continue running; repeat the command
to wait again. A `true` value only means the worker is no longer running (or was
never started), not that every task succeeded. Inspect `status.state`,
`status.failed`, and `status.worker_error`. A `completed` state includes tasks
that exhausted their retries; inspect `runner.failed()` for their errors.

## Resume after restart

After PythonHere restarts, reopen the named run, recreate resources and the
executor callable, then restart execution:

```python
runner = TaskRunner.open("data-import")
runner.start(execute_task)
```

Execution is at least once: an item interrupted by process death can run again.
Make irreversible executor side effects idempotent or check their durable state
before applying them. The executor runs in a background thread; marshal Kivy UI
access to the main thread according to `kivy-runtime.md`.
