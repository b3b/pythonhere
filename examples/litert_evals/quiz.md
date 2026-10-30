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

# Quiz

Companion notebook for the video [*Benchmarking Local AI on Android with PythonHere and Pydantic Evals*](https://youtu.be/CSwZkyGWrhU).

Run a six-question Python quiz against a model on your Android device, then
score its answers locally with [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/).

## Connect and configure

```{code-cell} ipython3
# %pip install pydantic-evals
```

```{code-cell} ipython3
%load_ext pythonhere
%connect-there
```

```{code-cell} ipython3
from herethere.everywhere import ConnectionConfig
from herethere.there import Client

client = Client()
await client.connect(ConnectionConfig.load(path="there.env", prefix="there"))
await client.ping()
```

We use the [LiteRT-LM version of Qwen2.5-Coder-3B-Instruct](https://huggingface.co/litert-community/Qwen2.5-Coder-3B-Instruct), with greedy decoding
and a 16-token answer limit. `%there put` copies these settings to the device for model loading and inference.

```{code-cell} ipython3
import os

settings = {
    "model_repo": "litert-community/Qwen2.5-Coder-3B-Instruct",
    "model_file": "Qwen2.5_Coder_3B_It.litertlm",
    "sampler": {"temperature": 1.0, "top_p": 1.0, "top_k": 1, "seed": 42},
    "max_output_tokens": 16,
}
hf_token = os.environ.get("HF_TOKEN")

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

## Load the model

The engine stays loaded across questions, but each answer uses a fresh
conversation so questions are answered independently.

```{code-cell} ipython3
%%there --worker
import litert_lm
from ml_here import require_model

if globals().get("quiz_engine") is not None:
    quiz_engine.close()
quiz_engine = None

quiz_engine = litert_lm.Engine(
    require_model(settings["model_repo"], settings["model_file"]),
    backend=litert_lm.Backend.GPU(),
)

def quiz_answer(prompt):
    with quiz_engine.create_conversation(
        sampler_config=litert_lm.SamplerConfig(**settings["sampler"]),
        max_output_tokens=settings["max_output_tokens"],
    ) as conversation:
        response = conversation.send_message(prompt)
    return "".join(block["text"] for block in response["content"] if "text" in block)

print(quiz_engine)
```

## Define questions

For this simple quiz, we define the questions directly in a Pydantic Evals
`Dataset`. Each `Case` contains a question, answer choices, and the expected
letter; `EqualsExpected()` scores the model's response against that letter.

```{code-cell} ipython3
from typing_extensions import TypedDict

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected


class QuestionInputs(TypedDict):
    question: str
    options: dict[str, str]


dataset = Dataset[QuestionInputs, str, None](
    name="python-quiz",
    cases=[
        Case(
            name="mutable-container",
            inputs={
                "question": "Which built-in type is mutable?",
                "options": {
                    "A": "tuple",
                    "B": "list",
                    "C": "str",
                    "D": "int",
                },
            },
            expected_output="B",
        ),
        Case(
            name="floor-division",
            inputs={
                "question": "What is the value of 7 // 2 in Python 3?",
                "options": {
                    "A": "3.5",
                    "B": "4",
                    "C": "2",
                    "D": "3",
                },
            },
            expected_output="D",
        ),
        Case(
            name="list-alias",
            inputs={
                "question": (
                    "What does this print?\n\n"
                    "a = [1, 2]\n"
                    "b = a\n"
                    "b.append(3)\n"
                    "print(a)"
                ),
                "options": {
                    "A": "[1, 2, 3]",
                    "B": "[1, 2]",
                    "C": "[3]",
                    "D": "None",
                },
            },
            expected_output="A",
        ),
        Case(
            name="empty-set",
            inputs={
                "question": "Which expression creates an empty set?",
                "options": {
                    "A": "{}",
                    "B": "[]",
                    "C": "set()",
                    "D": "()",
                },
            },
            expected_output="C",
        ),
        Case(
            name="mutable-default",
            inputs={
                "question": (
                    "What does the second call print?\n\n"
                    "def add(x, items=[]):\n"
                    "    items.append(x)\n"
                    "    return items\n\n"
                    "add(1)\n"
                    "print(add(2))"
                ),
                "options": {
                    "A": "[2]",
                    "B": "[1, 2]",
                    "C": "[]",
                    "D": "Raises TypeError",
                },
            },
            expected_output="B",
        ),
        Case(
            name="unpacking-comprehension-315",
            inputs={
                "question": (
                    "In Python 3.15, what does this print?\n\n"
                    "groups = [[1, 2], [3]]\n"
                    "print([*group for group in groups])"
                ),
                "options": {
                    "A": "SyntaxError",
                    "B": "[[1, 2], [3]]",
                    "C": "[1, 2, 3]",
                    "D": "TypeError",
                },
            },
            expected_output="C",
        ),
    ],
    evaluators=[EqualsExpected()],
)
```

## Define the task

```{code-cell} ipython3
def build_prompt(inputs: QuestionInputs) -> str:
    options = "\n".join(
        f"{letter}: {inputs['options'][letter]}"
        for letter in "ABCD"
    )
    return (
        "Answer the Python multiple-choice question.\n"
        "Exactly one option is correct.\n"
        "Reply with only A, B, C, or D. Do not explain.\n\n"
        f"{inputs['question'].rstrip()}\n\n"
        f"{options}\n\n"
        "Answer:"
    )

async def answer_question(inputs: QuestionInputs) -> str:
    prompt = build_prompt(inputs)
    response = await client.get_worker(f"quiz_answer({prompt!r})")
    return response.strip()
```

Inspect the prompt and try one question:

```{code-cell} ipython3
example = dataset.cases[0]
print(build_prompt(example.inputs))
```

```{code-cell} ipython3
print(repr(await answer_question(example.inputs)))
```

## Run and inspect

Scoring requires the expected letter alone, ignoring surrounding whitespace.
Extra explanation counts as a failed answer. Report durations include the client round trip.

```{code-cell} ipython3
report = await dataset.evaluate(answer_question, max_concurrency=1)
report.print(include_input=True, include_output=True, include_expected_output=True)
```

## Close the model and client

```{code-cell} ipython3
%%there --worker
quiz_engine.close()
quiz_engine = None
```

```{code-cell} ipython3
await client.disconnect()
```
