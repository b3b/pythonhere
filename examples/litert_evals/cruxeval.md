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

# CruxEval

Companion notebook for the video [*Benchmarking Local AI on Android with PythonHere and Pydantic Evals*](https://youtu.be/CSwZkyGWrhU).

Ask a model to predict Python function outputs from the
[CruxEval dataset](https://huggingface.co/datasets/cruxeval-org/cruxeval).
Generate answers in the background on Android, then score them locally with
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
and a 128-token answer limit. `%there put` copies the run name and settings
to the device.

`LIMIT=None` selects all 800 cases; set it to `3` for a short run. Reuse
`RUN_NAME` to resume, or choose a new name when changing the model, settings,
or selected cases. `REVISION` pins the dataset version.

```{code-cell} ipython3
import os
RUN_NAME = "cruxeval-qwen-direct-greedy-full-001"
LIMIT = None  # All cases.
REVISION = "b96af0450242eb4da433032b90998f25588a5d0f"
settings = {
    "model_repo": "litert-community/Qwen2.5-Coder-3B-Instruct",
    "model_file": "Qwen2.5_Coder_3B_It.litertlm",
    "sampler": {"temperature": 1.0, "top_p": 1.0, "top_k": 1, "seed": 42},
    "max_output_tokens": 128,
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

Each problem provides a function, an input, and an expected output. We use the
[CruxEval-O direct prompt](https://github.com/facebookresearch/cruxeval/blob/main/prompts.py)
to ask for the output; the expected answer stays local for scoring.

```{code-cell} ipython3
import ast
from datasets import load_dataset
from pprint import pprint as pp

rows = load_dataset("cruxeval-org/cruxeval", revision=REVISION, split="test")
if LIMIT is not None:
    rows = rows.select(range(LIMIT))
problems = [dict(row) for row in rows]
assert len({p["id"] for p in problems}) == len(problems)
for p in problems:
    ast.literal_eval(p["output"])
pp(f"Selected {len(problems)} cases")
```

```{code-cell} ipython3
def make_crux_prompt(inputs):
    code, input = inputs["code"], inputs["input"]
    instructions = (
        "You are given a Python function and an assertion containing an input "
        "to the function. Complete the assertion with a literal (no unsimplified "
        "expressions, no function calls) containing the output when executing "
        "the provided code on the given input, even if the function is incorrect "
        "or incomplete. Do NOT output any extra information. Provide the full "
        "assertion with the correct output in [ANSWER] and [/ANSWER] tags, "
        "following the examples."
    )

    return f"""{instructions}

[PYTHON]
def f(n):
    return n
assert f(17) == ??
[/PYTHON]
[ANSWER]
assert f(17) == 17
[/ANSWER]

[PYTHON]
def f(s):
    return s + "a"
assert f("x9j") == ??
[/PYTHON]
[ANSWER]
assert f("x9j") == "x9ja"
[/ANSWER]

[PYTHON]
{code}
assert f({input}) == ??
[/PYTHON]
[ANSWER]
"""
```

```{code-cell} ipython3
tasks = [{"id": p["id"], "prompt": make_crux_prompt(p)} for p in problems]
print(tasks[0]["prompt"])
```

## Start/resume answers generation run

`TaskRunner` saves answers on the device and continues after the notebook
disconnects. Reopening the same run resumes unfinished tasks. The engine is
shared across tasks, with a fresh conversation for each answer.

```{code-cell} ipython3
%there put tasks
```

```{code-cell} ipython3
%%there
from tasks_here import TaskRunner, TaskRunExistsError

try:
    crux_runner = TaskRunner.create(RUN_NAME, max_attempts=3, metadata=settings)
except TaskRunExistsError:
    crux_runner = TaskRunner.open(RUN_NAME)
if crux_runner.metadata != settings:
    raise ValueError("Device settings differ; choose a new RUN_NAME")
existing = [r["task"] for r in crux_runner.results()]
if existing and existing != tasks:
    raise ValueError("Device tasks differ; choose a new RUN_NAME")
if not existing:
    crux_runner.add(tasks)
print(crux_runner.status())
```

```{code-cell} ipython3
%%there
import litert_lm
from ml_here import require_model

def crux_setup():
    global crux_engine
    if globals().get("crux_engine") is not None:
        raise RuntimeError("Close previous crux_engine using the last cell before resuming")
    crux_engine = litert_lm.Engine(
        require_model(settings["model_repo"], settings["model_file"]),
        backend=litert_lm.Backend.GPU(), enable_benchmark=True,
    )
    return crux_engine

def crux_execute(task, engine):
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

if not crux_runner.is_running():
    crux_runner.start(crux_execute, setup=crux_setup)
print(crux_runner.status())
```

## Check progress and fetch the results

You can fetch and score completed answers while generation continues. After
reconnecting, rerun the configuration and run-opening cells to access the saved
run; there is no need to start generation again just to retrieve answers.

```{code-cell} ipython3
%there get crux_runner.status()
```

```{code-cell} ipython3
results = %there get crux_runner.results()
```

```{code-cell} ipython3
pp(results[-1])
```

## Score fetched answers locally

Score `results` directly. TaskRunner keeps results on the phone, so you can
fetch them again later. No model calls or generated-code execution during scoring.

We build a Pydantic Evals `Dataset` from completed answers and use a custom
`Evaluator` to extract each predicted Python literal and compare its value.
The report separates incorrect values from invalid answers that cannot be
parsed, such as unfinished literals or extra explanation.

`generation_s` is elapsed time measured by TaskRunner around the final
`crux_execute` call on the device, including conversation setup and cleanup.
Engine loading and earlier retries are excluded. `decode_tokens_s` is the
decoding speed reported by LiteRT's benchmark.

```{code-cell} ipython3
import ast
import io
import tokenize
from dataclasses import dataclass

from pydantic_evals import Case, Dataset, increment_eval_metric
from pydantic_evals.evaluators import Evaluator, EvaluationReason


def extract_crux_output(text):
    # LiteRT returns the stop marker as text; upstream generation strips it.
    candidate = text.split("[/ANSWER]", 1)[0]
    if "[ANSWER]" in candidate:
        candidate = candidate.split("[ANSWER]", 1)[1]

    # Find the assertion separator without splitting == inside quoted strings.
    if candidate.strip().startswith("assert "):
        lines = candidate.splitlines(keepends=True)
        for token in tokenize.generate_tokens(io.StringIO(candidate).readline):
            if token.type == tokenize.OP and token.string == "==":
                row, column = token.end
                candidate = "".join(lines[row - 1:])[column:]
                break

    return ast.literal_eval(candidate.strip())


@dataclass
class CruxLiteralMatch(Evaluator):
    def evaluate(self, ctx):
        expected = ast.literal_eval(ctx.expected_output)

        try:
            actual = extract_crux_output(ctx.output)
        except (SyntaxError, ValueError, TypeError, RecursionError, tokenize.TokenError) as exc:
            return {
                "passed": EvaluationReason(False, f"Invalid answer: {exc}"),
                "failure": "invalid",
            }

        if actual != expected:
            return {
                "passed": EvaluationReason(
                    False,
                    f"actual={actual!r}, expected={expected!r}",
                ),
                "failure": "incorrect",
            }

        return {"passed": True}
```

```{code-cell} ipython3
from collections import Counter
from pydantic_evals.evaluators import ReportEvaluator, ReportEvaluatorContext
from pydantic_evals.reporting.analyses import TableResult

@dataclass
class CruxSummary(ReportEvaluator):
    def evaluate(self, ctx: ReportEvaluatorContext):
        counts = Counter()

        for case in ctx.report.cases:
            assertion = case.assertions["passed"]

            if assertion.value:
                counts["passed"] += 1
            else:
                failure = case.labels.get("failure")
                if failure is None:
                    raise ValueError(
                        f"Missing failure label for {case.name}"
                    )
                counts[failure.value] += 1

        total = len(ctx.report.cases)

        return TableResult(
            title="CruxEval results",
            columns=["Scored", "Passed", "Pass rate", "Incorrect", "Invalid"],
            rows=[[
                total,
                counts["passed"],
                f"{counts['passed'] / total:.1%}" if total else "N/A",
                counts["incorrect"],
                counts["invalid"],
            ]],
        )
```

```{code-cell} ipython3
answers = {r["id"]: r["result"]["output"] for r in results if r["status"] == "done"}
completed = {r["id"]: r for r in results if r["status"] == "done"}

def saved_answer(case_id):
    record = completed[case_id]
    if record.get("duration") is not None:
        increment_eval_metric("generation_s", record["duration"])
    benchmark = record["result"].get("benchmark") or {}
    speed = benchmark.get("last_decode_tokens_per_second")
    if speed is not None:
        increment_eval_metric("decode_tokens_s", speed)
    return answers[case_id]

dataset = Dataset(
    name="cruxeval_o_literal_demo",
    cases=[Case(name=p["id"], inputs=p["id"], expected_output=p["output"])
           for p in problems if p["id"] in answers],
    evaluators=[CruxLiteralMatch()],
    report_evaluators=[CruxSummary()],
)
if not dataset.cases:
    raise RuntimeError("No completed answers; check device status/errors")
report = await dataset.evaluate(saved_answer, max_concurrency=1)

#report.print(include_durations=False, include_averages=True, include_reasons=True)
from dataclasses import replace
# Show the first eight cases; CruxSummary above covers all scored cases.
preview = replace(report, cases=report.cases[:8])
preview.print(include_durations=False, include_averages=False, include_analyses=True, include_reasons=True)
```

```{code-cell} ipython3
from rich.console import Console
from rich.table import Table
from rich.text import Text

invalid = [
    c for c in report.cases
    if c.labels.get("failure") is not None
    and c.labels["failure"].value == "invalid"
]

table = Table(title="Invalid answers")
table.add_column("Case", style="dim")
table.add_column("Output", overflow="fold")

for case in invalid:
    table.add_row(
        case.name,
        Text(repr(case.output)),
    )

Console().print(table)
```

## Close the engine

```{code-cell} ipython3
%%there --worker
if globals().get("crux_engine"):
    crux_engine.close()
    crux_engine = None
```
