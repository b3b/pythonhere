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

# <span style="color:#306998">Python</span><span style="color:#FFD43B">Here</span> 0.2.2 release intro

The intro was generated with `%%there ai` to show the PythonHere 0.2.x release features as a short audiovisual app.

Watch the result as a YouTube Short: https://www.youtube.com/shorts/ExN0YnTljVc

## Connect

```{code-cell} ipython3
%load_ext pythonhere
%connect-there
```

## Prompt used to generate the intro

````{code-cell} ipython3
%%there ai --prompts midi
You are the PythonHere 0.2.x release.
Express yourself as a short audiovisual demoscene-style intro.

Goal: generate a compact audiovisual intro.

Your release features:

```python
announcements = [
    {
        "title": "PythonHere 0.2.*",
        "subtitle": "the stack wakes again"
    },
    {
        "title": "GitHub Releases",
        "subtitle": "APK builds are back"
    },
    {
        "title": "%%there get {variable}",
        "subtitle": "get remote variables"
    },
    {
        "title": "%%there download {file}",
        "subtitle": "pull files from the target"
    },
    {
        "title": "%%there ai",
        "subtitle": "prompt -> cell"
    },
    {
        "title": "Generate -> Edit -> Run",
        "subtitle": "generated cells stay under your control"
    },
    {
        "title": "%%there ai --prompts masterpiece",
        "subtitle": "custom context / custom style"
    },
    {
        "title": "%%there ai --fix",
        "subtitle": "failure becomes feedback"
    },
]
```

Creative direction:
Make it feel like a compact demoscene intro built out of Kivy itself.

Use:

* dark background
* neon / terminal / retro-futurist mood
* rhythmic motion
* Kivy widgets used playfully as visual objects
* text effects
* short readable text beats
* autoplay when ready
* endless loop after the intro sequence
* single feature display at a time

Title is: PythonHere 0.2.x.

Make the version beat-synced:

* show `0.2.0`
* then `0.2.1`
* then `0.2.2`
* then `0.2.x`
* repeat this pattern every 16 sequencer steps

Make `Python` and `Here` with separate colors:

* Python: `#306998`
* Here: `#FFD43B`
* version: smaller cyan/white text

Core timing model:
Use one explicit 8-second / 64-step timing grid.

Constants must be:

```python
INTRO_SECONDS = 8.0
STEPS_PER_LOOP = 64
TICK_SECONDS = INTRO_SECONDS / STEPS_PER_LOOP
VISUAL_FPS = 30.0

FEATURES_PER_LOOP = 8
FEATURE_STEPS = STEPS_PER_LOOP // FEATURES_PER_LOOP  # 8

BLOCKS_PER_LOOP = 4
BLOCK_STEPS = STEPS_PER_LOOP // BLOCKS_PER_LOOP      # 16
```

Everything must derive from this sequencer grid:

* loop step: `0..63`
* musical block: `step // BLOCK_STEPS`
* local block step: `step % BLOCK_STEPS`
* feature card: `step // FEATURE_STEPS`
* beat marker: `step % BLOCK_STEPS`
* version character: `(step % BLOCK_STEPS) // 4`

The intro must be perfectly looped in 8 seconds:

* 64 sequencer steps total
* 8 feature cards total
* each feature card lasts exactly 8 sequencer steps
* 4 musical blocks total
* each musical block lasts exactly 16 sequencer steps
* loop returns exactly to the initial visual and musical state at step 0

Sequencer / MIDI clock:
The intro should be built around a live MIDI sequencer.

The sequencer step is the master state.
The Kivy Clock interval that calls `midi_tick` is the sequencer clock.
`midi_tick` advances exactly one integer step each tick.
Visuals must follow the sequencer state.

Do not derive visual state directly from `loop_start_time`.
Do not use `phase * len(announcements)` for feature cards.
Do not use independent wall-clock animation as the master.

Keep this state:

```python
self.step
self.last_played_step
self.last_tick_time
```

Use this helper for visual timing:

```python
def _loop_position(self):
    elapsed_since_tick = max(0.0, time.perf_counter() - self.last_tick_time)
    micro = min(0.999, elapsed_since_tick / TICK_SECONDS)

    step_float = self.last_played_step + micro
    step_float %= STEPS_PER_LOOP

    step = int(step_float)
    phase = step_float / STEPS_PER_LOOP

    return step, micro, phase
```

In `midi_tick`:

* if stopped, return `False`
* at the start of each sequencer tick, decrement active note lifetimes
* send `note_off` for notes whose `remaining_steps` reaches zero
* then generate MIDI events for the current integer `step`
* then send the new `note_on` events
* then add those notes to the active note list with `remaining_steps`
* then set `last_played_step = played_step`
* then set `last_tick_time = time.perf_counter()`
* then advance `step = (step + 1) % STEPS_PER_LOOP`

In `visual_tick`:

* never schedule MIDI
* never play MIDI
* never stop MIDI
* only read sequencer state
* call `_loop_position()`
* derive all visual state from `visual_step`, `micro`, and `phase`

Use this visual timing pattern:

```python
visual_step, micro, phase = self._loop_position()

feature_index = min(
    len(announcements) - 1,
    visual_step // FEATURE_STEPS,
)

local_feature_phase = (
    (visual_step % FEATURE_STEPS) + micro
) / FEATURE_STEPS

active16 = visual_step % BLOCK_STEPS

version_char = ["0", "1", "2", "x"][
    (visual_step % BLOCK_STEPS) // 4
]
```

Requirements:

* The intro should be built around a live MIDI sequencer.
* The sequencer state is the master clock.
* Visuals follow the sequencer state.
* Portrait Android mode.
* Text should always fit screen and containers.
* The result should not look like a normal app screen.
* Intro should be perfectly looped in 8 seconds.
* Should show all 8 features in 8 seconds.
* Should loop to exactly the initial state.
* Avoid audio slowdown by keeping `midi_tick` very lightweight.

Audio:
Generate and play a live MIDI looping synthpop positive rhythmic tune.

The tune must follow the 64-step grid:

* 64 steps per loop
* 4 musical blocks
* 16 steps per musical block
* use `block = step // BLOCK_STEPS`
* use `local = step % BLOCK_STEPS`
* drums, bass, lead, and chords should all loop exactly at step 64
* keep the MIDI event count per tick small
* avoid heavy computation inside `midi_tick`

Note lifetime:
Do not use `Clock.schedule_once` for every `note_off`.

Instead, keep a list of active notes with `remaining_steps`.

At the start of each sequencer tick:

* decrement `remaining_steps`
* send `note_off` for notes whose `remaining_steps` reaches zero

Then send new `note_on` events and add them to the active note list.

This keeps MIDI event scheduling deterministic and avoids many tiny callbacks.

Kivy visual concept:
Use ordinary Kivy widgets in extraordinary ways.

For example:

* Labels as glowing title cards
* Buttons as pulsing blocks or beat markers
* Sliders as oscilloscopes
* ProgressBars as equalizers
* BoxLayouts as moving panels
* canvas lines, grids, particles, waves, scanlines, or glow-like effects

The result should not look like a normal app screen.
It should look like a tiny audiovisual intro made from the runtime’s own UI system.

Kivy scheduling:
Use Kivy Clock carefully.

Allowed:

* one `Clock.schedule_interval` for the MIDI sequencer tick
* one `Clock.schedule_interval` for lightweight visual refresh

Not allowed:

* many scheduled callbacks
* `Clock.schedule_once` for every MIDI note-off
* rebuilding layouts every frame
* creating/destroying widgets during animation
* recalculating installed distributions during animation
* calling `texture_update` every frame
* scheduling MIDI events from the visual update function
* creating new canvas instructions during animation
* creating large temporary lists during animation

Performance:

* `midi_tick` must be extremely lightweight
* package scanning must happen once before animation starts
* runtime ticker string must be built once before animation starts
* widgets must be created once
* canvas instructions must be created once
* animation should update existing widget properties and existing canvas instructions only
* visual update may set existing `Color.rgba`, `Line.points`, `Rectangle.pos`, `Rectangle.size`, `Label.text`, `Label.opacity`, `Slider.value`, and `ProgressBar.value`
* avoid expensive work in both scheduled callbacks
* never let visual effects slow down MIDI timing

Effects:
Use canvas for effects.

Runtime scroller:
Create a continuous demoscene-style ticker at the bottom or edge of the screen.

The scroller must use real runtime information, not hardcoded fake package versions.

Build it dynamically once before animation starts:

* Use `sys.version_info` for the real Python interpreter version
* Use `[f"{dist.metadata['Name']}=={dist.version}" for dist in distributions()]` for installed packages
* Format the ticker like: `PYTHON==3.x.x | Kivy==2.3.1 | cffi==... | ...`

Ticker timing:

* ticker starts outside the right edge of the screen
* text is not visible at the first frame
* ticker moves from right to left
* ticker position is derived from sequencer `phase`
* ticker returns to exactly the initial outside-right position when `phase` wraps to `0`
* perfect loop sync is more important than showing every package clearly
* if the ticker text is very long, it does not need to fully reveal every package in one loop

Use this ticker motion model:

```python
ticker.x = self.ui.width - phase * (self.ui.width + self.ui._ticker_width)
```
````

## Generated intro code

```{code-cell} ipython3
%%there
# Generated locally by %%there ai. Review before running.
from importlib.metadata import distributions
import math
import sys
import time

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp, sp
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.label import Label

from midistream import Synthesizer, MIDIException, ReverbPreset
from midistream.helpers import (
    Control,
    midi_control_change,
    midi_instruments,
    midi_note_off,
    midi_note_on,
    midi_program_change,
)

INTRO_SECONDS = 8.0
STEPS_PER_LOOP = 64
TICK_SECONDS = INTRO_SECONDS / STEPS_PER_LOOP
VISUAL_FPS = 30.0

FEATURES_PER_LOOP = 8
FEATURE_STEPS = STEPS_PER_LOOP // FEATURES_PER_LOOP  # 8

BLOCKS_PER_LOOP = 4
BLOCK_STEPS = STEPS_PER_LOOP // BLOCKS_PER_LOOP      # 16

announcements = [
    {"title": "PythonHere 0.2.*", "subtitle": "the stack wakes again"},
    {"title": "GitHub Releases", "subtitle": "APK builds are back"},
    {"title": "%%there get {variable}", "subtitle": "get remote variables"},
    {"title": "%%there download {path}", "subtitle": "pull files from the target"},
    {"title": "%%there ai", "subtitle": "prompt -> cell"},
    {"title": "Generate -> Edit -> Run", "subtitle": "generated cells stay under your control"},
    {"title": "%%there ai --prompts masterpiece", "subtitle": "custom context / custom style"},
    {"title": "%%there ai --fix", "subtitle": "failure becomes feedback"},
]

try:
    previous_intro = globals().get("pythonhere_intro_controller")
    if previous_intro is not None:
        previous_intro.stop(close_midi=False)
except Exception:
    Logger.exception("PythonHere: Could not stop previous intro")

if "midistream_active_notes" not in globals():
    midistream_active_notes = set()
if "midistream_used_channels" not in globals():
    midistream_used_channels = set()

installed_runtime_packages = [f"{dist.metadata['Name']}=={dist.version}" for dist in distributions()]
pythonhere_intro_ticker_text = (
    f"PYTHON=={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    + " | "
    + " | ".join(installed_runtime_packages)
)

pythonhere_intro_state = {
    "ok": False,
    "stage": "initializing",
    "message": "Building PythonHere 0.2.x intro",
    "error": None,
}


def get_synthesizer():
    global synthesizer
    if "synthesizer" not in globals() or synthesizer is None:
        synthesizer = Synthesizer()
    return synthesizer


class IntroRoot(FloatLayout):
    pass


KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<IntroRoot>:
    Label:
        id: deck_label
        text: "LIVE GRID 64 / MIDI CLOCK / KIVY CORE"
        size_hint: 0.94, None
        height: dp(22)
        pos_hint: {"center_x": 0.5, "top": 0.998}
        color: 0.25, 0.95, 1.0, 0.82
        font_size: sp(10)
        bold: True
        halign: "center"
        valign: "middle"
        text_size: self.size

    BoxLayout:
        id: title_band
        orientation: "horizontal"
        padding: dp(4), 0
        spacing: dp(2)
        size_hint: 0.96, None
        height: dp(74)
        pos_hint: {"center_x": 0.5, "top": 0.965}

        Label:
            id: python_label
            text: "Python"
            color: 0.188, 0.412, 0.596, 1
            font_size: sp(32)
            bold: True
            halign: "right"
            valign: "middle"
            text_size: self.size
            size_hint_x: 0.42

        Label:
            id: here_label
            text: "Here"
            color: 1.0, 0.831, 0.231, 1
            font_size: sp(32)
            bold: True
            halign: "left"
            valign: "middle"
            text_size: self.size
            size_hint_x: 0.30

        Label:
            id: version_label
            text: "0.2.0"
            color: 0.65, 1.0, 1.0, 1
            font_size: sp(18)
            bold: True
            halign: "left"
            valign: "middle"
            text_size: self.size
            size_hint_x: 0.28

    BoxLayout:
        id: feature_panel
        orientation: "vertical"
        padding: dp(12), dp(8)
        spacing: dp(4)
        size_hint: 0.92, 0.30
        pos_hint: {"center_x": 0.5, "center_y": 0.595}
        canvas.before:
            Color:
                rgba: 0.02, 0.09, 0.12, 0.78
            Rectangle:
                pos: self.pos
                size: self.size
            Color:
                rgba: 0.0, 0.85, 1.0, 0.28
            Line:
                rectangle: self.x, self.y, self.width, self.height
                width: 1.2

        Label:
            id: feature_title
            text: ""
            color: 0.70, 1.0, 1.0, 1
            font_size: sp(22)
            bold: True
            halign: "center"
            valign: "middle"
            text_size: self.width - dp(18), self.height
            shorten: True
            shorten_from: "right"
            size_hint_y: 0.58

        Label:
            id: feature_subtitle
            text: ""
            color: 1.0, 0.88, 0.42, 1
            font_size: sp(15)
            halign: "center"
            valign: "middle"
            text_size: self.width - dp(18), self.height
            shorten: True
            shorten_from: "right"
            size_hint_y: 0.42

    BoxLayout:
        id: osc_bank
        orientation: "vertical"
        spacing: dp(4)
        size_hint: 0.88, None
        height: dp(86)
        pos_hint: {"center_x": 0.5, "center_y": 0.315}

        Slider:
            id: osc_a
            min: 0
            max: 100
            value: 0

        Slider:
            id: osc_b
            min: 0
            max: 100
            value: 0

        Slider:
            id: osc_c
            min: 0
            max: 100
            value: 0

    BoxLayout:
        id: meter_bank
        orientation: "vertical"
        spacing: dp(2)
        size_hint: 0.88, None
        height: dp(70)
        pos_hint: {"center_x": 0.5, "y": 0.145}

    BoxLayout:
        id: beat_row
        orientation: "horizontal"
        spacing: dp(2)
        size_hint: 0.94, None
        height: dp(34)
        pos_hint: {"center_x": 0.5, "y": 0.085}

    Label:
        id: status_label
        text: "arming sequencer"
        size_hint: 0.96, None
        height: dp(24)
        pos_hint: {"center_x": 0.5, "y": 0.048}
        color: 0.55, 1.0, 0.84, 0.9
        font_size: sp(10)
        bold: True
        halign: "center"
        valign: "middle"
        text_size: self.size
        shorten: True
        shorten_from: "right"

    Label:
        id: ticker
        text: ""
        size_hint: None, None
        height: dp(24)
        x: root.width
        y: dp(3)
        color: 0.20, 1.0, 0.58, 0.92
        font_size: sp(10)
        bold: True
        halign: "left"
        valign: "middle"
        text_size: None, self.height

IntroRoot:
"""


def build_midi_pattern():
    roots = [48, 45, 41, 43]
    chords = [
        [60, 64, 67],
        [57, 60, 64],
        [53, 57, 60],
        [55, 59, 62],
    ]
    leads = [
        [72, 74, 76, 79, 76, 74],
        [69, 72, 76, 81, 76, 72],
        [65, 69, 72, 77, 72, 69],
        [67, 71, 74, 79, 83, 79],
    ]
    lead_slots = [2, 5, 7, 10, 13, 15]
    bass_slots = [0, 3, 6, 8, 11, 14]
    pattern = [[] for _ in range(STEPS_PER_LOOP)]

    for step in range(STEPS_PER_LOOP):
        block = step // BLOCK_STEPS
        local = step % BLOCK_STEPS
        root_note = roots[block]

        if local in (0, 8):
            pattern[step].append((9, 36, 108, 1))
        if local in (4, 12):
            pattern[step].append((9, 38, 96, 1))
        if local % 2 == 0:
            pattern[step].append((9, 42, 62, 1))
        if local == 14:
            pattern[step].append((9, 46, 72, 1))

        if local in bass_slots:
            bass_note = root_note if local in (0, 6, 8, 14) else root_note + 7
            pattern[step].append((0, bass_note, 92, 2))

        if local in (0, 8):
            for chord_note in chords[block]:
                pattern[step].append((2, chord_note, 50, 7))

        if local in lead_slots:
            lead_index = lead_slots.index(local)
            pattern[step].append((1, leads[block][lead_index], 78, 2))

    return pattern


class PythonHereIntroController:
    def __init__(self, ui, ticker_text, cards):
        self.ui = ui
        self.cards = cards
        self.ticker_text = ticker_text
        self.step = 0
        self.last_played_step = 0
        self.last_tick_time = time.perf_counter()
        self.running = False
        self.midi_enabled = True
        self.midi_error = None
        self.active_notes = []
        self.used_channels = {0, 1, 2, 9}
        self.midi_event = None
        self.visual_event = None
        self.current_feature_index = None
        self.current_version_text = None
        self.note_pattern = build_midi_pattern()
        self.beat_buttons = []
        self.meters = []
        self.particle_items = []
        self.grid_lines = []
        self.scan_color = None
        self.scan_rect = None
        self.wave_color = None
        self.wave_line = None
        self.bg_rect = None
        self.bg_color = None
        self._setup_widgets()
        self._setup_canvas()
        self.ui.bind(pos=self._resize_canvas, size=self._resize_canvas)
        self._resize_canvas()

    def _setup_widgets(self):
        self.ui.ids.ticker.text = self.ticker_text
        self.ui.ids.ticker.texture_update()
        self.ui._ticker_width = max(1, int(self.ui.ids.ticker.texture_size[0]))
        self.ui.ids.ticker.width = self.ui._ticker_width

        for index in range(16):
            btn = Button(
                text=f"{index:02d}",
                font_size=sp(9),
                bold=True,
                background_normal="",
                background_down="",
                color=(0.65, 1.0, 1.0, 0.85),
            )
            btn.background_color = (0.02, 0.12, 0.16, 0.70)
            self.ui.ids.beat_row.add_widget(btn)
            self.beat_buttons.append(btn)

        for index in range(8):
            meter = ProgressBar(max=100, value=0)
            self.ui.ids.meter_bank.add_widget(meter)
            self.meters.append(meter)

    def _setup_canvas(self):
        with self.ui.canvas.before:
            self.bg_color = Color(0.005, 0.008, 0.018, 1.0)
            self.bg_rect = Rectangle(pos=self.ui.pos, size=self.ui.size)

            for _ in range(10):
                color = Color(0.0, 0.45, 0.58, 0.10)
                line = Line(points=[0, 0, 0, 0], width=0.8)
                self.grid_lines.append((color, line))

            self.wave_color = Color(0.0, 0.95, 1.0, 0.52)
            self.wave_line = Line(points=[], width=1.4)

            self.scan_color = Color(0.2, 1.0, 0.75, 0.10)
            self.scan_rect = Rectangle(pos=(0, 0), size=(1, dp(3)))

            for i in range(28):
                color = Color(0.20, 1.0, 0.75, 0.0)
                dot = Ellipse(pos=(0, 0), size=(dp(2), dp(2)))
                self.particle_items.append((color, dot, i))

    def _resize_canvas(self, *args):
        w = max(1.0, float(self.ui.width))
        h = max(1.0, float(self.ui.height))
        self.bg_rect.pos = self.ui.pos
        self.bg_rect.size = self.ui.size

        for i, pair in enumerate(self.grid_lines):
            color, line = pair
            if i < 5:
                x = w * (i + 1) / 6.0
                line.points = [x, 0, x, h]
            else:
                y = h * (i - 4) / 6.0
                line.points = [0, y, w, y]
            color.rgba = (0.0, 0.55, 0.70, 0.08)

    def _program_synth(self):
        global midistream_used_channels
        synth = get_synthesizer()
        synth.volume = 86
        synth.reverb = ReverbPreset.ROOM
        setup = []
        setup += midi_program_change(38, channel=0)
        setup += midi_program_change(81, channel=1)
        setup += midi_program_change(88, channel=2)
        setup += midi_control_change(Control.volume, 104, channel=0)
        setup += midi_control_change(Control.volume, 92, channel=1)
        setup += midi_control_change(Control.volume, 70, channel=2)
        setup += midi_control_change(Control.pan, 44, channel=0)
        setup += midi_control_change(Control.pan, 82, channel=1)
        setup += midi_control_change(Control.pan, 64, channel=2)
        synth.write(setup)
        midistream_used_channels.update(self.used_channels)

    def _safe_note_off_list(self, notes):
        global midistream_active_notes
        if not notes or not self.midi_enabled:
            return
        cmd = []
        for channel, note in notes:
            cmd += midi_note_off(note, channel=channel, velocity=0)
        get_synthesizer().write(cmd)
        for channel, note in notes:
            midistream_active_notes.discard((channel, note))

    def all_sound_off(self):
        global midistream_active_notes
        if not self.midi_enabled:
            self.active_notes = []
            midistream_active_notes.clear()
            return
        try:
            off_notes = [(channel, note) for channel, note, _remaining in self.active_notes]
            if off_notes:
                self._safe_note_off_list(off_notes)
            cmd = []
            for channel in sorted(self.used_channels):
                cmd += midi_control_change(Control.all_sound_off, 0, channel=channel)
            get_synthesizer().write(cmd)
        except Exception:
            Logger.exception("PythonHere: Could not silence intro MIDI")
        self.active_notes = []
        midistream_active_notes.clear()

    def start(self):
        pythonhere_intro_state.update(
            ok=True,
            stage="running",
            message="PythonHere 0.2.x intro running",
            error=None,
        )
        self.running = True
        try:
            self._program_synth()
            self.ui.ids.status_label.text = "MIDI locked / 64 step loop / visual clock slaved"
        except Exception as exc:
            self.midi_enabled = False
            self.midi_error = f"{type(exc).__name__}: {exc}"
            pythonhere_intro_state.update(
                ok=False,
                stage="midi_init",
                message="Visual intro running without MIDI",
                error=self.midi_error,
            )
            self.ui.ids.status_label.text = "MIDI init failed / visual clock continues"
            Logger.exception("PythonHere: Could not initialize MIDI intro")

        self.visual_tick(0)
        self.midi_tick(0)
        self.midi_event = Clock.schedule_interval(self.midi_tick, TICK_SECONDS)
        self.visual_event = Clock.schedule_interval(self.visual_tick, 1.0 / VISUAL_FPS)

    def stop(self, close_midi=False):
        self.running = False
        if self.midi_event is not None:
            self.midi_event.cancel()
            self.midi_event = None
        if self.visual_event is not None:
            self.visual_event.cancel()
            self.visual_event = None
        self.all_sound_off()
        if close_midi:
            try:
                synth = globals().get("synthesizer")
                if synth is not None:
                    synth.close()
                globals()["synthesizer"] = None
            except Exception:
                Logger.exception("PythonHere: Could not close synthesizer")
        pythonhere_intro_state.update(
            ok=True,
            stage="stopped",
            message="PythonHere intro stopped",
            error=None,
        )

    def _loop_position(self):
        elapsed_since_tick = max(0.0, time.perf_counter() - self.last_tick_time)
        micro = min(0.999, elapsed_since_tick / TICK_SECONDS)

        step_float = self.last_played_step + micro
        step_float %= STEPS_PER_LOOP

        step = int(step_float)
        phase = step_float / STEPS_PER_LOOP

        return step, micro, phase

    def midi_tick(self, dt):
        global midistream_active_notes, midistream_used_channels
        if not self.running:
            return False

        played_step = self.step

        if self.midi_enabled:
            try:
                expired = []
                survivors = []
                for channel, note, remaining_steps in self.active_notes:
                    remaining_steps -= 1
                    if remaining_steps <= 0:
                        expired.append((channel, note))
                    else:
                        survivors.append((channel, note, remaining_steps))
                self.active_notes = survivors

                if expired:
                    self._safe_note_off_list(expired)

                events = self.note_pattern[played_step]
                if events:
                    cmd = []
                    for channel, note, velocity, _duration in events:
                        cmd += midi_note_on(note, channel=channel, velocity=velocity)
                    get_synthesizer().write(cmd)

                    for channel, note, _velocity, duration in events:
                        self.active_notes.append((channel, note, duration))
                        midistream_active_notes.add((channel, note))
                        midistream_used_channels.add(channel)
                        self.used_channels.add(channel)

            except MIDIException as exc:
                self.midi_enabled = False
                self.midi_error = f"{type(exc).__name__}: {exc}"
                pythonhere_intro_state.update(
                    ok=False,
                    stage="midi_tick",
                    message="MIDI disabled after sequencer error",
                    error=self.midi_error,
                )
                self.ui.ids.status_label.text = "MIDI error / visual sequencer still loops"
                Logger.exception("PythonHere: MIDI intro tick failed")
            except Exception as exc:
                self.midi_enabled = False
                self.midi_error = f"{type(exc).__name__}: {exc}"
                pythonhere_intro_state.update(
                    ok=False,
                    stage="midi_tick",
                    message="MIDI disabled after sequencer error",
                    error=self.midi_error,
                )
                self.ui.ids.status_label.text = "MIDI error / visual sequencer still loops"
                Logger.exception("PythonHere: MIDI intro tick failed")

        self.last_played_step = played_step
        self.last_tick_time = time.perf_counter()
        self.step = (self.step + 1) % STEPS_PER_LOOP
        pythonhere_intro_state["step"] = played_step
        pythonhere_intro_state["next_step"] = self.step
        return True

    def visual_tick(self, dt):
        if not self.running:
            return False

        visual_step, micro, phase = self._loop_position()

        feature_index = min(
            len(self.cards) - 1,
            visual_step // FEATURE_STEPS,
        )

        local_feature_phase = (
            (visual_step % FEATURE_STEPS) + micro
        ) / FEATURE_STEPS

        active16 = visual_step % BLOCK_STEPS

        version_char = ["0", "1", "2", "x"][
            (visual_step % BLOCK_STEPS) // 4
        ]
        version_text = "0.2." + version_char

        block = visual_step // BLOCK_STEPS
        local = visual_step % BLOCK_STEPS

        if feature_index != self.current_feature_index:
            card = self.cards[feature_index]
            self.ui.ids.feature_title.text = card["title"]
            self.ui.ids.feature_subtitle.text = card["subtitle"]
            title_len = len(card["title"])
            self.ui.ids.feature_title.font_size = sp(18 if title_len > 28 else 22)
            self.current_feature_index = feature_index

        if version_text != self.current_version_text:
            self.ui.ids.version_label.text = version_text
            self.current_version_text = version_text

        fade_in = min(1.0, local_feature_phase * 5.5)
        fade_out = min(1.0, (1.0 - local_feature_phase) * 5.5)
        panel_alpha = max(0.0, min(fade_in, fade_out))
        pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * ((active16 + micro) / BLOCK_STEPS))

        self.ui.ids.feature_panel.opacity = 0.62 + 0.38 * panel_alpha
        self.ui.ids.python_label.opacity = 0.82 + 0.18 * pulse
        self.ui.ids.here_label.opacity = 0.82 + 0.18 * (1.0 - pulse)
        self.ui.ids.version_label.color = (
            0.72 + 0.20 * pulse,
            1.0,
            1.0,
            1.0,
        )

        for i, btn in enumerate(self.beat_buttons):
            distance = min((i - active16) % BLOCK_STEPS, (active16 - i) % BLOCK_STEPS)
            intensity = max(0.0, 1.0 - distance / 5.0)
            if i == active16:
                btn.background_color = (0.05, 0.95, 1.0, 0.98)
                btn.color = (0.0, 0.02, 0.04, 1.0)
            elif i % 4 == 0:
                btn.background_color = (0.18, 0.34 + 0.24 * intensity, 0.62, 0.78)
                btn.color = (0.78, 1.0, 1.0, 0.82)
            else:
                btn.background_color = (0.02, 0.11 + 0.22 * intensity, 0.16 + 0.28 * intensity, 0.70)
                btn.color = (0.42, 0.95, 1.0, 0.74)

        for i, meter in enumerate(self.meters):
            meter.value = 8 + 86 * abs(math.sin(2.0 * math.pi * (phase * (i + 1) + i * 0.091)))

        self.ui.ids.osc_a.value = 50 + 48 * math.sin(2.0 * math.pi * (phase * 4.0))
        self.ui.ids.osc_b.value = 50 + 48 * math.sin(2.0 * math.pi * (phase * 8.0 + 0.18))
        self.ui.ids.osc_c.value = 50 + 48 * math.sin(2.0 * math.pi * (phase * 16.0 + 0.37))

        w = max(1.0, float(self.ui.width))
        h = max(1.0, float(self.ui.height))

        self.ui.ids.ticker.x = self.ui.width - phase * (self.ui.width + self.ui._ticker_width)

        scan_y = ((visual_step + micro) / STEPS_PER_LOOP) * h
        self.scan_rect.pos = (0, scan_y)
        self.scan_rect.size = (w, dp(3))
        self.scan_color.rgba = (0.0, 1.0, 0.72, 0.06 + 0.08 * pulse)

        wave_points = []
        base_y = h * 0.455
        amp = h * 0.025
        for i in range(32):
            x = w * i / 31.0
            y = base_y + amp * math.sin(2.0 * math.pi * (phase * 8.0 + i / 7.0))
            wave_points.extend([x, y])
        self.wave_line.points = wave_points
        self.wave_color.rgba = (0.0, 0.82 + 0.18 * pulse, 1.0, 0.34 + 0.22 * pulse)

        for color, dot, i in self.particle_items:
            px = (w * ((i * 37) % 101) / 100.0 + phase * w * (0.25 + (i % 5) * 0.06)) % w
            py = h * (0.20 + 0.62 * (((i * 19) % 97) / 96.0))
            py += math.sin(2.0 * math.pi * (phase * (1 + (i % 4)) + i * 0.13)) * h * 0.018
            size = dp(1.6 + (i % 4))
            dot.pos = (px, py)
            dot.size = (size, size)
            color.rgba = (
                0.18 + 0.12 * (i % 3),
                0.78 + 0.22 * pulse,
                1.0,
                0.18 + 0.22 * ((i + active16) % 4 == 0),
            )

        self.ui.ids.status_label.text = (
            f"STEP {visual_step:02d}/63  BLOCK {block + 1}/4  LOCAL {local:02d}  "
            f"FEATURE {feature_index + 1}/8"
        )

        pythonhere_intro_state["visual_step"] = visual_step
        pythonhere_intro_state["phase"] = phase
        pythonhere_intro_state["feature_index"] = feature_index
        pythonhere_intro_state["version"] = version_text

        return True


def stop_pythonhere_intro(close_midi=False):
    controller = globals().get("pythonhere_intro_controller")
    if controller is not None:
        controller.stop(close_midi=close_midi)


try:
    pythonhere_intro_ui = Builder.load_string(KV)
    if pythonhere_intro_ui is None:
        raise RuntimeError("Builder.load_string(KV) returned None")

    pythonhere_intro_controller = PythonHereIntroController(
        pythonhere_intro_ui,
        pythonhere_intro_ticker_text,
        announcements,
    )

    root.clear_widgets()
    root.add_widget(pythonhere_intro_ui)

    pythonhere_intro_controller.start()


except Exception as exc:
    pythonhere_last_error = f"{type(exc).__name__}: {exc}"
    pythonhere_intro_state.update(
        ok=False,
        stage="setup_failed",
        message="Could not start PythonHere 0.2.x intro",
        error=pythonhere_last_error,
    )
    Logger.exception("PythonHere: Could not start PythonHere 0.2.x intro")
    Popup(
        title="PythonHere intro error",
        content=Label(
            text=pythonhere_last_error,
            text_size=(dp(280), None),
            halign="center",
            valign="middle",
        ),
        size_hint=(0.86, 0.34),
    ).open()
```
