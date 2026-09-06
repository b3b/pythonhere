# ML model helpers for LiteRT

PythonHere provides `ml_here` for acquiring and locating ML model files. It
does not wrap LiteRT-LM inference.

All public model helpers return paths as strings (a list of strings for
`discover_models()`), ready to pass to `litert_lm.Engine()`.

```python
from ml_here import (
    discover_models,
    download_hf_model,
    model_path,
    models_directory,
    require_model,
)
```

- `models_directory(create=False)` returns PythonHere's model directory. On
  Android this is the app-specific external files directory under `models`; on
  Linux it is `~/.local/share/pythonhere/models`.
- `model_path(repo_id, filename)` returns the namespaced path for a model. It
  does not create directories and rejects unsafe path components.
- `require_model(repo_id, filename)` returns that path when the model is
  installed and raises `FileNotFoundError` otherwise.
- `discover_models(extra_directories=(), extensions=".litertlm")` recursively
  returns sorted, unique LiteRT-LM model paths from managed storage and any
  additional directories. Pass another extension or iterable to select other
  formats, or `extensions=None` to include every completed stored artifact.
- `download_hf_model(repo_id, filename, *, revision="main", token=None,
  destination=None, progress=None, cancelled=None, overwrite=False,
  expected_sha256=None)` downloads a Hugging Face model file of any format. By
  default, it stores the file at `model_path(repo_id, filename)`.

Choose by intent: use `require_model()` to load a known installed model, the
path returned by `download_hf_model()` after a download, and
`discover_models()` only to inventory models whose identities are not already
known. Use `model_path()` when only the expected location is needed.

Downloads are resumable across restarts and make the final file visible only
after the download completes. Cancellation preserves the partial download for
resuming. Pass a token for private or gated models. The `progress` callback
receives the following interface; use it directly rather than redefining it:

```python
class DownloadProgress:
    repo_id: str
    filename: str
    destination: str
    downloaded: int
    total: int | None
    elapsed: float
    speed_bps: float
    fraction: float | None
    percent: float | None
    speed_mbps: float
    remaining: int | None
    eta: float | None
```

Use `litert_lm` directly to load and run the returned model path.

## Run an installed model

Run model loading and inference on a worker (`--worker`) to keep Kivy
responsive. In the app runtime, import model helpers from `ml_here`.

```python
import litert_lm
from ml_here import require_model

model_file = require_model(
    "litert-community/SmolLM2-135M-Instruct",
    "SmolLM2_135M_Instruct.litertlm",
)
engine = litert_lm.Engine(model_file)
try:
    with engine.create_conversation(max_output_tokens=128) as conversation:
        response = conversation.send_message(
            "What is the Kivy framework? Answer in one short paragraph."
        )
        text = "".join(
            part["text"]
            for part in response["content"]
            if part.get("type") == "text"
        )
        print(text)
finally:
    engine.close()
```

The conversation closes before the engine, including when inference raises.
For an interactive chat, keep the engine loaded and reuse the conversation
for follow-up messages; close both when the chat is finished.

`litert_lm.Engine(model_file)` uses CPU by default. For a model and device
that support GPU inference, replace the engine construction above with:

```python
engine = litert_lm.Engine(model_file, backend=litert_lm.Backend.GPU())
```

## Download first when needed

If the model is not installed, download it on a worker before inference:

```python
from ml_here import download_hf_model

model_file = download_hf_model(
    "litert-community/SmolLM2-135M-Instruct",
    "SmolLM2_135M_Instruct.litertlm",
)
print(model_file)
```

When downloading and loading in the same script, pass the returned
`model_file` directly to `litert_lm.Engine()`.

See the [upstream Python API](https://github.com/google-ai-edge/LiteRT-LM/tree/main/python)
for streaming, sampling, and multimodal inference.
