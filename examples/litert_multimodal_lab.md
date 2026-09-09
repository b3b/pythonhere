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

# LiteRT multimodal lab

Companion notebook for the video [*Run multimodal AI on Android with Python and LiteRT*](https://youtu.be/w_RZ0Y29A7I).

## Connect to PythonHere

```{code-cell} ipython3
%load_ext pythonhere
%connect-there
```

## Show download progress

```{code-cell} ipython3
%%there kv
<DownloadProgress>:
    size_hint: .82, .82
    pos_hint: {'center_x': .5, 'center_y': .5}

    canvas:
        Color:
            rgba: .45, .52, .50, .16

        Line:
            width: dp(5)
            circle:
                self.center_x, \
                self.center_y, \
                min(self.width, self.height) * .34, \
                0, \
                360

        Color:
            rgba: .30, .40, .37, .95 if root.value > 0 else 0

        Line:
            width: dp(10) if root.value >= 100 else dp(9)
            circle:
                self.center_x, \
                self.center_y, \
                min(self.width, self.height) * .34, \
                105, \
                105 + 360 * min(max(root.value, 0), 100) / 100

    Label:
        text: "Ready" if root.value >= 100 else f"{root.value:3.0f}%"
        font_size: min(root.width, root.height) * (.11 if root.value >= 100 else .13)
        color: .25, .32, .30, .95
        center: root.center
```

```{code-cell} ipython3
%%there
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget


class DownloadProgress(Widget):
    value = NumericProperty(0)

root.clear_widgets()
progress = DownloadProgress()
root.add_widget(progress)
```

## Download the model

```{code-cell} ipython3
%%there --worker
from pprint import pprint as pp
from kivy.clock import mainthread
from ml_here import download_hf_model, require_model

MODEL_REPO = "litert-community/SmolVLM2-500M"
MODEL_FILE = "SmolVLM2-500M.litertlm"


@mainthread
def update_progress(value):
    progress.value = value.percent or 0.0


download_hf_model(
    repo_id=MODEL_REPO,
    filename=MODEL_FILE,
    progress=update_progress,
)

pp(require_model(MODEL_REPO, MODEL_FILE))
```

## Load the model

```{code-cell} ipython3
%%there --worker
import litert_lm
engine = litert_lm.Engine(
    require_model(MODEL_REPO, MODEL_FILE),
    backend=litert_lm.Backend.GPU(),
    vision_backend=litert_lm.Backend.GPU(),
    enable_benchmark=True,
)
pp(engine)
```

## Generate text

### Create a streaming output view

```{code-cell} ipython3
%%there kv
<ModelOutput>:
    size_hint: .88, .7
    pos_hint: {'center_x': .5, 'center_y': .5}

    Label:
        markup: True
        text: root.text
        font_size: dp(21)
        halign: "left"
        valign: "top"
        text_size: root.width, None
        pos: root.pos
        size: root.size
```

```{code-cell} ipython3
%%there
from kivy.properties import StringProperty
from kivy.uix.widget import Widget
from kivy.clock import mainthread


class ModelOutput(Widget):
    text = StringProperty("")
    committed = StringProperty("")
    newest = StringProperty("")

    @mainthread
    def append_chunk(self, chunk):
        self.committed += self.newest
        self.newest = chunk
        self.text = (
            f"[color=#E8EEF3]{self.committed}[/color]"
            f"[color=#FFD343][b]{self.newest}[/b][/color]"
        )

root.clear_widgets()
output = ModelOutput()
root.add_widget(output)
```

### Ask a text question

```{code-cell} ipython3
%%there --worker

sampler = litert_lm.SamplerConfig(
    temperature=0.7,
    top_p=0.9,
    top_k=40,
)

with engine.create_conversation(
    sampler_config=sampler,
    max_output_tokens=128,
) as conversation:
    for chunk in conversation.send_message_async(
        "What is on-device AI? Give a direct answer in one short paragraph."
    ):
        output.append_chunk(chunk["content"][0]["text"])
    info = conversation.get_benchmark_info()
    output.append_chunk("")
```

### Show benchmark results

```{code-cell} ipython3
%%there
print(
    "\n\tBenchmark info for the conversation\n"
    f"Init:    {info.init_time_in_second:.2f}s\n"
    f"TTFT:    {info.time_to_first_token_in_second:.2f}s\n"
    f"Prefill: {info.last_prefill_token_count} tokens "
    f"@ {info.last_prefill_tokens_per_second:.1f} tok/s\n"
    f"Decode:  {info.last_decode_token_count} tokens "
    f"@ {info.last_decode_tokens_per_second:.1f} tok/s"
)
```

## Describe a camera photo

### Request camera permission

```{code-cell} ipython3
%%there
from threading import Event
from android.permissions import Permission, request_permission

done = Event()
request_permission(Permission.CAMERA, lambda *_: done.set())
done.wait()
```

### Preview and capture a photo

```{code-cell} ipython3
%%there kv
AnchorLayout:
    anchor_x: "center"
    anchor_y: "center"

    Camera:
        id: camera
        play: True
        resolution: (640, 480)
        fit_mode: "contain"

        size_hint: None, None
        height: min(root.width, root.height * 3 / 4)
        width: self.height * 4 / 3

        canvas.before:
            PushMatrix
            Rotate:
                angle: -90
                origin: self.center

        canvas.after:
            PopMatrix
```

```{code-cell} ipython3
%%there
camera = root.ids.camera
camera.play = False
```

```{code-cell} ipython3
%%there
from os.path import abspath, getsize
from PIL import Image

texture = camera.texture
image = Image.frombytes("RGBA", texture.size, texture.pixels)

# Kivy textures use a bottom-left origin.
image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Match the rotation applied to the Android camera preview.
image = image.rotate(-90, expand=True).convert("RGB")

photo_path = abspath("from_camera.jpg")
image.save(photo_path, quality=90)

print(f"Photo: {photo_path}")
print(
    f"Image: {image.width} × {image.height}, "
    f"{image.mode}, {getsize(photo_path) / 1024:.1f} KiB"
)
```

### Generate a description

```{code-cell} ipython3
%%there --worker
sampler = litert_lm.SamplerConfig(
    temperature=0.7,
    top_p=0.9,
    top_k=40,
)

with engine.create_conversation(
    sampler_config=sampler,
    max_output_tokens=96,
) as conversation:
    response = conversation.send_message(
        litert_lm.Contents.of(
            "Describe the main object in this image clearly and concisely in 2-3 sentences.",
            litert_lm.Content.ImageFile(absolute_path=photo_path),
        )
    )
    print(response["content"][0]["text"])
```

## Explore sampling variability

### Generate responses with different temperatures and seeds

```{code-cell} ipython3
%%there --worker
prompt = (
    "Describe the main object in this image clearly and concisely "
    "in 2-3 sentences."
)

temperatures = [0.2, 0.5, 0.7, 1.0]
seeds = [1, 7, 42, 123, 999]

experiment_results = []

for temperature in temperatures:
    for seed in seeds:
        sampler = litert_lm.SamplerConfig(
            temperature=temperature,
            top_p=0.9,
            top_k=40,
            seed=seed,
        )

        with engine.create_conversation(
            sampler_config=sampler,
            max_output_tokens=96,
        ) as conversation:
            response = conversation.send_message(
                litert_lm.Contents.of(
                    prompt,
                    litert_lm.Content.ImageFile(absolute_path=photo_path),
                )
            )

            info = conversation.get_benchmark_info()

        experiment_results.append({
            "temperature": temperature,
            "seed": seed,
            "output": response["content"][0]["text"].strip(),
            "ttft_s": info.time_to_first_token_in_second,
            "prefill_tokens": info.last_prefill_token_count,
            "prefill_tok_s": info.last_prefill_tokens_per_second,
            "decode_tokens": info.last_decode_token_count,
            "decode_tok_s": info.last_decode_tokens_per_second,
        })

print(f"Done: {len(experiment_results)} runs")
```

### Compare the outputs

```{code-cell} ipython3
import pandas as pd

experiment_results = %there get experiment_results

df = pd.DataFrame(experiment_results)

display(
    df[
        [
            "temperature",
            "seed",
            "decode_tokens",
            "output",
        ]
    ].style
    .format({
        "temperature": "{:.1f}",
    })
    .set_properties(
        subset=["output"],
        **{
            "white-space": "pre-wrap",
            "text-align": "left",
        },
    )
    .hide(axis="index")
)
```

## Clean up

```{code-cell} ipython3
%%there --worker
engine.close()
```
