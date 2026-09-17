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

```{code-cell} ipython3
%load_ext pythonhere
%connect-there
```

## Submit and start work

Every task needs a unique nonempty string `id`. Tasks and returned results must
contain plain JSON-compatible values.

```{code-cell} ipython3
%%there
import time

from tasks_here import TaskRunner


def execute_task(task, context):
    time.sleep(1)
    return {
        "value": task["value"],
        "square": task["value"] ** 2,
    }


runner = TaskRunner.create("squares-example", max_attempts=3)
runner.add([{"id": str(value), "value": value} for value in range(1, 11)])
runner.start(execute_task)
```

`start()` returns promptly while the runner processes tasks in its background
thread.

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

## Inspect progress and results

```{code-cell} ipython3
status = %there get runner.status()
status
```

Results can be inspected while work is still running:

```{code-cell} ipython3
results = %there get runner.results()
results
```

## Wait for completion

Run this cell to wait up to 50 seconds while keeping the device's UI responsive:

```{code-cell} ipython3
%%there --worker
stopped = runner.wait(timeout=50)
print("Worker stopped:", stopped)
print(runner.status())
```

If `stopped` is `False`, tasks are still running; run the cell again to keep
waiting. `True` means the worker has stopped, which can also happen after a
pause or an error. A `completed` state includes tasks that exhausted their
retries. Inspect any failures from the notebook:

```{code-cell} ipython3
failures = %there get runner.failed()
failures
```

## Pause and resume

`pause()` lets the current task finish and stops before claiming another. Wait
for that graceful pause before inspecting its final paused state:

```{code-cell} ipython3
%%there --worker
runner.pause()
runner.wait(timeout=10)
print(runner.status())
```

Resume the remaining tasks with the same executor:

```{code-cell} ipython3
%%there
runner.start(execute_task)
```

## Reopen after PythonHere restarts

The task list and results are persistent, but Python callables and other runtime
objects are not. After restarting PythonHere, reconnect, recreate the executor,
open the named run, and start it again:

```{code-cell} ipython3
%%there
import time

from tasks_here import TaskRunner


def execute_task(task, context):
    time.sleep(1)
    return {
        "value": task["value"],
        "square": task["value"] ** 2,
    }


runner = TaskRunner.open("squares-example")
runner.start(execute_task)
```

Execution is at least once. If PythonHere stops after an executor begins but
before its result is committed, that task can run again. Executors with
irreversible side effects should therefore be idempotent or check durable state
before applying those effects.
