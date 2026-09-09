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

# On-device AI with LiteRT

PythonHere bundles the
[LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM) Python library in its
Android app, so `.litertlm` models can run directly on the device. After a
model has been downloaded, inference does not require a network connection.

PythonHere also provides
[model helpers](https://github.com/b3b/pythonhere/tree/main/pythonhere/ml_here)
for managing model storage and downloading model files from Hugging Face.
This example covers every public helper, then loads a small language model and
generates text with LiteRT-LM. Refer to the LiteRT-LM documentation for its
full inference API, including sampling, streaming, and benchmarking.

For an interactive vision-language example using the Android camera, see the
[LiteRT multimodal lab](litert_multimodal_lab.md), the companion notebook for
the video *Run multimodal AI on Android with Python and LiteRT*.

## Connect to PythonHere

Load the Jupyter extension and connect to a running PythonHere app:

```{code-cell} ipython3
%load_ext pythonhere
%connect-there
```

## Inspect model storage

`models_directory()` returns PythonHere's platform-specific model directory.
`model_path()` builds the managed path for a particular Hugging Face model,
and `discover_models()` lists models already present on the device.

```{code-cell} ipython3
%%there
from pprint import pprint as pp
from ml_here import (
    discover_models,
    download_hf_model,
    model_path,
    models_directory,
    require_model,
)

MODEL_REPO = "litert-community/SmolLM2-135M-Instruct"
MODEL_FILE = "SmolLM2_135M_Instruct.litertlm"

print(f"Model directory: {models_directory(create=True)}")
print(f"Managed path: {model_path(MODEL_REPO, MODEL_FILE)}")
print("Available LiteRT-LM models:")
pp(discover_models())
```

## Download the model

`download_hf_model()` downloads the model into its managed path. Downloads
can be resumed, and an existing verified file is reused. Because downloading
may take time, this cell runs on a worker so the Android UI stays responsive.

```{code-cell} ipython3
%%there --worker
def report_progress(value):
    if value.percent is not None:
        print(f"\rDownloading: {value.percent:.1f}%", end="", flush=True)


downloaded_path = download_hf_model(
    repo_id=MODEL_REPO,
    filename=MODEL_FILE,
    progress=report_progress,
)

print(f"\nDownloaded model: {downloaded_path}")
```

`require_model()` returns the model path if the file is available and raises
`FileNotFoundError` otherwise. Discover the device again to confirm that the
downloaded model is now included:

```{code-cell} ipython3
%%there
model_file = require_model(MODEL_REPO, MODEL_FILE)
print(f"Required model: {model_file}")
print("Available LiteRT-LM models:")
pp(discover_models())
```

## Load the model

Model loading and inference can block the app's UI thread, so they also run
with `%%there --worker`.

```{code-cell} ipython3
%%there --worker
import litert_lm

engine = litert_lm.Engine(model_file)
pp(engine)
```

## Generate text

Create a conversation and send a prompt. The model runs locally in the
PythonHere app, and only the generated response is returned to Jupyter.

```{code-cell} ipython3
%%there --worker
with engine.create_conversation(
    max_output_tokens=128,
) as conversation:
    response = conversation.send_message(
        "What is the Kivy framework? Answer in one short paragraph."
    )
    pp(response["content"][0]["text"])
```

## Clean up

Close the engine to release its native resources when it is no longer needed:

```{code-cell} ipython3
%%there --worker
engine.close()
```
