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

# LeetCode

Companion notebook for the video [*Benchmarking Local AI on Android with PythonHere and Pydantic Evals*](https://youtu.be/CSwZkyGWrhU).

Generate Python solutions on Android using
[newfacade/LeetCodeDataset](https://huggingface.co/datasets/newfacade/LeetCodeDataset),
then run the dataset's tests locally with
[Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/).

## Connect and configure

```{code-cell} ipython3
# %pip install pydantic-evals datasets
```

```{code-cell} ipython3
%load_ext pythonhere
%connect-there
```

We use the [LiteRT-LM version of Qwen2.5-Coder-3B-Instruct](https://huggingface.co/litert-community/Qwen2.5-Coder-3B-Instruct)
with greedy decoding (`top_k=1`), seed 42,
and a 1,000-token answer limit. `%there put` copies the run name and settings
to the device.

`LIMIT=None` selects the full test split; set it to `3` for a short run.
Reuse `RUN_NAME` to resume, or choose a new name when changing settings or
selected cases. `REVISION` pins the dataset version.

```{code-cell} ipython3
import os
RUN_NAME = "leetcode-qwen-greedy-full-001"
LIMIT = None  # All cases.
REVISION = "215604aeed660029df7de2fea5a4d7b6ed476a08"
settings = {
    "model_repo": "litert-community/Qwen2.5-Coder-3B-Instruct",
    "model_file": "Qwen2.5_Coder_3B_It.litertlm",
    "sampler": {"temperature": 1.0, "top_p": 1.0, "top_k": 1, "seed": 42},
    "max_output_tokens": 1000,
    "dataset_revision": REVISION,
}
hf_token = os.environ.get("HF_TOKEN")

%there put RUN_NAME
%there put settings
%there put hf_token
```

## Download the model

```{code-cell} ipython3
%%there --worker
from ml_here import download_hf_model, require_model

try:
    model = require_model(settings["model_repo"], settings["model_file"])
except FileNotFoundError:
    def report_progress(value):
        if value.percent is not None:
            print(f"\rDownloading: {value.percent:.1f}%", end="", flush=True)

    model = download_hf_model(
        repo_id=settings["model_repo"],
        filename=settings["model_file"],
        token=hf_token,
        progress=report_progress,
    )

print(model)
```

## Load dataset and build prompts

We send each problem's original `query` to the model. Tests stay local and
are used only for scoring. Inspect one prompt and its tests below.

```{code-cell} ipython3
from datasets import load_dataset
from pprint import pprint as pp

rows = load_dataset("newfacade/LeetCodeDataset", revision=REVISION, split="test")
if LIMIT is not None:
    rows = rows.select(range(LIMIT))
problems = [dict(row) for row in rows]
assert problems, "No cases selected"
assert len({p["task_id"] for p in problems}) == len(problems)
pp(f"Selected {len(problems)} cases")
```

```{code-cell} ipython3
print(problems[0]["query"])
```

```{code-cell} ipython3
print(problems[0]["test"])
```

```{code-cell} ipython3
tasks = [
    {"id": p["task_id"], "prompt": p["query"],
     "metadata": {"difficulty": p["difficulty"].lower()}}
    for p in problems
]
```

## Start/resume answers generation run

`TaskRunner` saves answers on the device and continues after the notebook
disconnects. Starting the same named run processes unfinished tasks. The engine
is shared across tasks, with a fresh conversation for each solution.

```{code-cell} ipython3
%there put tasks
```

```{code-cell} ipython3
%%there
from tasks_here import TaskRunner, TaskRunExistsError

try:
    leetcode_runner = TaskRunner.create(RUN_NAME, max_attempts=3, metadata=settings)
except TaskRunExistsError:
    leetcode_runner = TaskRunner.open(RUN_NAME)

existing = [r["task"] for r in leetcode_runner.results()]
if not existing:
    leetcode_runner.add(tasks)

```

```{code-cell} ipython3
%%there
import litert_lm
from ml_here import require_model

def leetcode_setup():
    global leetcode_engine
    if globals().get("leetcode_engine") is not None:
        raise RuntimeError("Close previous leetcode_engine using the last cell before resuming")
    leetcode_engine = litert_lm.Engine(
        require_model(settings["model_repo"], settings["model_file"]),
        backend=litert_lm.Backend.GPU(), enable_benchmark=True,
    )
    return leetcode_engine

def leetcode_execute(task, engine):
    with engine.create_conversation(
        sampler_config=litert_lm.SamplerConfig(**settings["sampler"]),
        max_output_tokens=settings["max_output_tokens"],
    ) as conversation:
        response = conversation.send_message(task["prompt"])
        try:
            info = conversation.get_benchmark_info()
            benchmark = {k: getattr(info, k) for k in (
                "init_time_in_second", "time_to_first_token_in_second",
                "last_prefill_token_count", "last_prefill_tokens_per_second",
                "last_decode_token_count", "last_decode_tokens_per_second",
            )}
            benchmark_error = None
        except Exception as exc:
            benchmark, benchmark_error = None, str(exc)
    return {
        "output": "".join(b["text"] for b in response["content"] if "text" in b),
        "benchmark": benchmark, "benchmark_error": benchmark_error,
    }

if not leetcode_runner.is_running():
    leetcode_runner.start(leetcode_execute, setup=leetcode_setup)
print(leetcode_runner.status())
```

## Check progress and fetch the results

Completed answers can be fetched and scored while generation continues.
After reconnecting, rerun the configuration and run-opening cells to retrieve
saved answers without starting generation again.

```{code-cell} ipython3
%there get leetcode_runner.status()
```

```{code-cell} ipython3
results = %there get leetcode_runner.results()
```

```{code-cell} ipython3
pp(results[-1])
```

## Score fetched answers locally

We build a Pydantic Evals `Dataset` from completed answers. The custom
`LeetCodePass` evaluator extracts Python code and runs each solution with its
tests in a local subprocess, with a 10-second timeout. The difficulty summary
separates passes, assertion failures, invalid answers, syntax errors, runtime
errors, and timeouts.

`generation_s` is TaskRunner's elapsed time around the final `leetcode_execute`
call on the device, including conversation setup and cleanup but excluding
engine loading and earlier retries. `decode_tokens_s` is the decoding speed
reported by LiteRT's benchmark.

```{code-cell} ipython3
import sys
import json
import re
import subprocess
from dataclasses import dataclass

from pydantic_evals import Case, Dataset, increment_eval_metric
from pydantic_evals.evaluators import Evaluator, EvaluationReason


def extract_python_code(text):
    fences = re.findall(r"```([^\n`]*)\n(.*?)```", text, flags=re.DOTALL)
    if fences:
        if len(fences) != 1 or fences[0][0].strip().lower() not in {"", "python", "py"}:
            raise ValueError("Expected one Python code block")
        code = fences[0][1].strip()
    elif "```" in text:
        raise ValueError("Incomplete code block")
    else:
        code = text.strip()
    if not code:
        raise ValueError("Empty code")
    return code


def execute_problem(problem, code, timeout):
    program = "\n".join([
        problem["prompt"], code, problem["test"],
        f"check({problem['entry_point']})",
    ])
    # Report success only after the complete program and tests return.
    harness = f'''
import json
try:
    exec(compile({program!r}, "<solution>", "exec"), {{}})
except SyntaxError as exc:
    result = {{"outcome": "syntax_error", "error": str(exc)}}
except AssertionError as exc:
    result = {{"outcome": "test_failed", "error": "AssertionError: " + str(exc)}}
except BaseException as exc:
    result = {{"outcome": "runtime_error", "error": type(exc).__name__ + ": " + str(exc)}}
else:
    result = {{"outcome": "passed"}}
print("__TEST_RESULT__" + json.dumps(result))
'''
    try:
        process = subprocess.run(
            [sys.executable, "-I", "-"], input=harness,
            text=True, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"outcome": "timeout", "error": f"Exceeded {timeout:g} seconds"}
    for line in reversed(process.stdout.splitlines()):
        if line.startswith("__TEST_RESULT__"):
            return json.loads(line[len("__TEST_RESULT__"):])
    return {"outcome": "runtime_error", "error": process.stderr.strip() or "Tests did not finish"}


@dataclass
class LeetCodePass(Evaluator):
    problems: dict
    timeout: float = 10.0

    def evaluate(self, ctx):
        try:
            code = extract_python_code(ctx.output)
        except ValueError as exc:
            return {
                "passed": EvaluationReason(False, str(exc)),
                "failure": "invalid",
            }

        problem = self.problems[ctx.inputs]
        result = execute_problem(problem, code, self.timeout)
        if result["outcome"] == "passed":
            return {"passed": True}
        return {
            "passed": EvaluationReason(False, result.get("error") or result["outcome"]),
            "failure": result["outcome"],
        }
```

```{code-cell} ipython3
from collections import Counter
from pydantic_evals.evaluators import ReportEvaluator, ReportEvaluatorContext
from pydantic_evals.reporting.analyses import TableResult


@dataclass
class LeetCodeSummary(ReportEvaluator):
    def evaluate(self, ctx: ReportEvaluatorContext):
        categories = ["passed", "test_failed", "invalid", "syntax_error",
                      "runtime_error", "timeout"]
        rows = []
        for difficulty in ["all", "easy", "medium", "hard"]:
            cases = [c for c in ctx.report.cases
                     if difficulty == "all" or c.metadata["difficulty"] == difficulty]
            if not cases:
                continue
            counts = Counter()
            for case in cases:
                if case.assertions["passed"].value:
                    counts["passed"] += 1
                else:
                    counts[case.labels["failure"].value] += 1
            rows.append([difficulty, len(cases),
                         *[round(100 * counts[name] / len(cases), 1)
                           for name in categories]])
        return TableResult(
            title="LeetCode results by difficulty",
            columns=["Difficulty", "N", "Passed %", "Assertion %", "Invalid %",
                     "Syntax %", "Runtime %", "Timeout %"],
            rows=rows,
        )
```

```{code-cell} ipython3
problems_by_id = {p["task_id"]: p for p in problems}
completed = {r["id"]: r for r in results if r["status"] == "done"}
for case_id, record in completed.items():
    if case_id not in problems_by_id or record["task"]["prompt"] != problems_by_id[case_id]["query"]:
        raise ValueError("Fetched tasks differ from selected dataset")

def saved_answer(case_id):
    record = completed[case_id]
    if record.get("duration") is not None:
        increment_eval_metric("generation_s", record["duration"])
    benchmark = record["result"].get("benchmark") or {}
    speed = benchmark.get("last_decode_tokens_per_second")
    if speed is not None:
        increment_eval_metric("decode_tokens_s", speed)
    return record["result"]["output"]

dataset = Dataset(
    name="pythonhere-leetcode",
    cases=[Case(name=p["task_id"], inputs=p["task_id"],
                metadata={"difficulty": p["difficulty"].lower()})
           for p in problems if p["task_id"] in completed],
    evaluators=[LeetCodePass(problems_by_id)],
    report_evaluators=[LeetCodeSummary()],
)
if not dataset.cases:
    raise RuntimeError("No completed answers; check device status/errors")
report = await dataset.evaluate(saved_answer, max_concurrency=1)

# report.print(include_durations=False, include_averages=True, include_reasons=True)
from dataclasses import replace
# Show the first eight cases; LeetCodeSummary covers all scored cases.
preview = replace(report, cases=report.cases[:8])
preview.print(include_durations=False, include_averages=False, include_analyses=True, include_reasons=True)
```

Show bad answers that are missing `class Solution`.

```{code-cell} ipython3
from rich.console import Console
from rich.table import Table
from rich.text import Text

weird = [
    r["result"]["output"]
    for r in results
    if r["status"] == "done"
    and "class Solution" not in r["result"]["output"]
]

table = Table(title=f"Unexpected outputs ({len(weird)})")
table.add_column("#", style="dim", justify="right")
table.add_column("Output", overflow="fold")

for r in results:
    if r["status"] == "done":
        s = r["result"]["output"]
        if "class Solution" not in s:
            table.add_row(r["id"], Text(repr(s[:300])))

Console().print(table)
```

Another bad answer from the video starts with `class Solution`, but keeps
adding nested loops until the output is cut off. Show that problem's saved answer:

```{code-cell} ipython3
example_id = "find-the-lexicographically-largest-string-from-the-box-i"
if example_id in completed:
    print(completed[example_id]["result"]["output"])
else:
    print(f"No saved answer for {example_id} in this run.")
```

## Close the engine

```{code-cell} ipython3
%%there --worker
if globals().get("leetcode_engine") is not None:
    leetcode_engine.close()
    leetcode_engine = None
```
