---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.19.3
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Prompt-to-cell generation

`%%there ai` turns a plain-language request into a new `%%there` Python cell.
The generated cell is inserted in the notebook below the prompt cell. Review or
edit it, then run it on the connected PythonHere device.

The AI command is provided by the underlying `herethere` library. PythonHere
adds Android/Kivy prompt sections on top of it. For the generic library
behavior, see the `herethere` docs:
https://herethere.me/library/there_ai.html

```{code-cell}
%load_ext pythonhere
%connect-there
```

## Configure an AI provider

`%%there ai` uses an OpenAI-compatible chat API. Put provider settings in
`there_ai.env` next to the notebook:

```text
# Model name for the OpenAI-compatible chat/completions API
THERE_AI_MODEL=

# API key for hosted providers; leave empty for local providers
THERE_AI_API_KEY=

# OpenAI-compatible API base URL
THERE_AI_BASE_URL=https://api.openai.com/v1

# Sampling temperature for generated code
THERE_AI_TEMPERATURE=0.2

# Request timeout in seconds
THERE_AI_TIMEOUT=300
```

Only `THERE_AI_MODEL` is required for local providers that do not need an API
key. Hosted providers usually need `THERE_AI_API_KEY`.

`THERE_AI_BASE_URL` defaults to `https://api.openai.com/v1`.
`THERE_AI_TEMPERATURE` defaults to `0.2`.
`THERE_AI_TIMEOUT` defaults to `300` seconds.

Internally, `%%there ai` sends a POST request to
`${THERE_AI_BASE_URL}/chat/completions` with `model`, `messages`, and
`temperature`, and uses `Authorization: Bearer ${THERE_AI_API_KEY}` when an API
key is configured. See the
[OpenAI-compatible adapter](https://github.com/b3b/herethere/blob/master/herethere/there/ai/llm.py)
for the current implementation.

Environment variables with the same names override values from `there_ai.env`:

```{code-cell}
:tags: ["remove-output"]
%env THERE_AI_TIMEOUT=120
```

Use a different settings file for the current notebook session:

```{code-cell}
from herethere.there.ai import set_ai_config_path

set_ai_config_path("there_ai.local.env")
```

Example local-provider settings:

```text
THERE_AI_MODEL=qwen2.5-coder
THERE_AI_BASE_URL=http://localhost:11434/v1
THERE_AI_TEMPERATURE=0.1
THERE_AI_TIMEOUT=300
```

## First generated cell

Write the request in the cell body:

```{code-cell}
:tags: ["remove-output"]
%%there ai
Inspect the live PythonHere runtime.
Print Python version, Kivy platform, current working directory, screen size,
and whether globals named app and root are available.
Store the structured result in pythonhere_ai_runtime_report.
```

The generated cell will be inserted locally as a `%%there` cell. Read it before
running it on the connected device.

It may look like this:

```python
%%there
# Generated locally by %%there ai. Review before running.
import os
import platform
import sys

from kivy import platform as kivy_platform
from kivy.core.window import Window

pythonhere_ai_runtime_report = {
    "python": sys.version,
    "platform": platform.platform(),
    "kivy_platform": kivy_platform,
    "cwd": os.getcwd(),
    "window_size": tuple(Window.size),
    "has_app": "app" in globals(),
    "has_root": "root" in globals(),
    "root_class": root.__class__.__name__ if "root" in globals() else None,
}

for key, value in pythonhere_ai_runtime_report.items():
    print(f"{key}: {value}")
```

## PythonHere prompt context

When you load `%load_ext pythonhere`, PythonHere registers prompt sections for
Kivy, Android, Pyjnius, permissions, packages, media, and Plyer. Normal
`%%there ai` requests use that context automatically.

For tasks that need extra context, add a prompt section for one request:

```{code-cell}
:tags: ["remove-output"]
%%there ai --prompts able
Build a BLE scanner prototype that lists discovered devices with name, address,
RSSI, and last-seen time.
```

For the full prompt list, source links, custom prompt registration, and prompt
composition rules, see [Prompt sections](prompts.md).

## Fix a previous cell

`%%there ai --fix` generates a replacement `%%there` cell. The AI request uses
the active system prompt stack plus the built-in `fix` prompt section. Its user
message includes the last executed Python `%%there` magic line, that cell body,
and the text you write in the `--fix` cell. It does not automatically include
previous output, traceback text, screenshots, remote variables, or live device
state. Paste the important error message or requested change into the `--fix`
cell body. The old cell is not changed.

Run a broken cell:

```{code-cell}
%%there
root.clear_widgets()
root.add_widget(Button(text="Click me))
```

Then ask for a fix:

```{code-cell}
:tags: ["remove-output"]
%%there ai --fix
SyntaxError
```

```{code-cell}
%%there
# Generated locally by %%there ai. Review before running.
# AI mode: fix
# Fix: close the string quote and import Button before using it.
from kivy.uix.button import Button

root.clear_widgets()
root.add_widget(Button(text="Click me"))
```
