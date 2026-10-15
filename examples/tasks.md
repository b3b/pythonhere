---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.3
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Durable sequential tasks

`TaskRunner` runs tasks one at a time in the PythonHere process and persists
their inputs, results, errors, and retry state. Work continues if Jupyter
disconnects. After PythonHere restarts, completed tasks remain complete and an
interrupted task becomes runnable again.

## Connect to PythonHere

```{code-cell} python
%load_ext pythonhere
%connect-there
```

## Submit and start work

Every task needs a unique nonempty string `id`. Tasks and returned results must
contain plain JSON-compatible values. If `"squares-example"` already exists
from an earlier attempt, use a new name or delete the old run with the
[cleanup cell](#clean-up) at the end.

```{code-cell} python
%%there
import time

from tasks_here import TaskRunner


def execute_task(task, context):
    time.sleep(1)
    if task["value"] == 5:
        raise ValueError("Intentional example failure for value 5")
    return {
        "value": task["value"],
        "square": task["value"] ** 2,
    }


runner = TaskRunner.create("squares-example", max_attempts=3)
runner.add([{"id": str(value), "value": value} for value in range(1, 11)])
runner.start(execute_task)
```

`start()` returns promptly while tasks run one at a time in a background thread.
The task for value `5` deliberately fails. With `max_attempts=3`, the runner
tries it three times before marking it failed; the other nine tasks still run.
Including retries, this example takes about twelve seconds. Tasks continue
running between notebook cells, so the run may already be completed when you
inspect it.

## Inspect progress and results

```{code-cell} python
status = %there get runner.status()
status
```

You can inspect results before the whole run finishes:

```{code-cell} python
:tags: ["hide-output"]
results = %there get runner.results()
results
```

To wait briefly before checking progress again:

```{code-cell} python
%%there --worker
runner.wait(timeout=1)
print(runner.status())
```

This waits at most one second and returns sooner if the worker has stopped.

## Pause and resume (optional)

While tasks are still running, you can pause them. `pause()` lets the current
task finish, and `wait()` waits for the pause to take effect:

```{code-cell} python
%%there --worker
runner.pause()
runner.wait()
print(runner.status())
```

Resume any pending tasks with the same executor. Completed tasks are kept:

```{code-cell} python
%%there
runner.start(execute_task)
```

If all tasks have already completed, there is nothing left to pause or resume.

## Wait for completion

Wait for all remaining work, then show the final counts. `--worker` keeps the
app's UI responsive while this cell waits:

```{code-cell} python
%%there --worker
runner.wait()
status = runner.status()
print("State:", status["state"])
print("Completed:", status["completed"], "of", status["total"])
print("Failed:", status["failed"])
```

Expected output:

```text
State: completed
Completed: 9 of 10
Failed: 1
```

`wait()` returns when the worker stops. A `completed` state means all tasks
have been processed, including any that exhausted their retries; it does not
mean every task succeeded. Inspect the deliberately failed task:

```{code-cell} python
failures = %there get runner.failed()
failures
```

The failed record has `id: "5"`, `attempt_count: 3`, `failure_count: 3`,
and the intentional `ValueError`. The other nine tasks have their square results.

## Export results

For larger results, export a JSON snapshot on the device and download the file:

```{code-cell} python
%%there --worker
runner.export_results("task-results.json")
```

```{code-cell} python
%there download task-results.json ./task-results.json
```

Load the downloaded file in the notebook:

```{code-cell} python
import json

with open("task-results.json", encoding="utf-8") as f:
    results = json.load(f)
```

The export includes all task records, including pending and failed tasks, in
submission order. Export after completion for final results, or during execution
for a snapshot. Relative paths use the device's current working directory,
which is PythonHere's upload directory by default. For large runs, exporting
and downloading a file avoids transferring all results through `%there get`.

## Reopen after PythonHere restarts

The task list and results are persistent, but Python callables and other runtime
objects are not. After restarting PythonHere, reconnect, recreate the executor,
open the named run, and start it again. Completed tasks are kept; only
unfinished work runs again. If all ten tasks already finished, the run stays
completed.

In this walkthrough, all tasks have already finished. Reopening shows that
the results and the failed task survived the restart. The task that exhausted
its retries stays failed; calling `start()` does not retry it again. To try recovery of unfinished work separately,
restart the app while a fresh run is executing, then reconnect and run this cell:

```{code-cell} python
%%there
import time

from tasks_here import TaskRunner


def execute_task(task, context):
    time.sleep(1)
    if task["value"] == 5:
        raise ValueError("Intentional example failure for value 5")
    return {
        "value": task["value"],
        "square": task["value"] ** 2,
    }


runner = TaskRunner.open("squares-example")
runner.start(execute_task)
```

Wait for any unfinished work, then inspect the saved results:

```{code-cell} python
%%there --worker
runner.wait()
print(runner.status())
```

```{code-cell} python
:tags: ["hide-output"]
saved_results = %there get runner.results()
saved_results
```

Execution is at least once. If PythonHere stops after an executor begins but
before its result is committed, that task can run again. Executors with
irreversible side effects should therefore be idempotent or check durable state
before applying those effects.

## Optional: reuse runtime resources

The executor always receives a second argument. It is `None` when `start()` has
no setup callback. For expensive runtime resources, create them once per worker
session and reuse the returned context for every task and retry:

```python
def setup():
    return create_runtime()


def execute_with_runtime(task, runtime):
    return runtime.process(task)


runner.start(execute_with_runtime, setup=setup)
```

Setup runs in the background worker thread, so `start()` still returns promptly.
While setup executes, `runner.status()["state"]` is `"setting_up"`; after setup
succeeds it becomes `"running"` before the first task is claimed.
If pause is requested while setup is running, setup finishes and the worker exits
before claiming a task. A later `start()` calls setup again. Context is runtime
state: it is not persisted or included in results, and the runner does not close
it automatically. Applications that require deterministic resource cleanup must
manage that cleanup themselves.

## Clean up

When you are done inspecting the completed run, you can delete it to repeat
this example with the same name. Skip this cell to keep its saved results.
This deletes only `"squares-example"` and its tasks/results; other runs and
exported JSON files are untouched.

```{code-cell} python
%%there --worker
from tasks_here import TaskRunner, TaskRunNotFoundError

try:
    saved_run = TaskRunner.open("squares-example")
except TaskRunNotFoundError:
    print("The example run has already been deleted.")
else:
    saved_run.delete()
    print("Example run deleted. You can now run the example again.")
```

A running task run cannot be deleted. Finish or pause it first.
