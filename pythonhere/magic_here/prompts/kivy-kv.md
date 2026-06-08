## Kv design

Use KV for layout only:
- widget tree
- ids
- simple widget properties
- simple canvas instructions

Critical generated-KV constraints:
- If KV uses `dp(...)` or `sp(...)`, the KV string must include the matching
  `#:import` line once at the top, before widget rules.
- If KV uses `sin(...)`, `cos(...)`, `abs(...)`, `min(...)`, or any other helper
  function in an expression, the name must be defined in KV parser scope with
  `#:import` or the calculation must be moved into Python.
- Do not use KV dynamic class/template syntax such as `<Name@BaseWidget>:` in
  generated PythonHere snippets.
- Do not call `Builder.template(...)`; use `ui = Builder.load_string(KV)`.
- Do not put callbacks in KV. Bind callbacks in Python after
  `Builder.load_string(KV)`.
- Do not use `app.some_method()` or `root.some_method()` in KV callbacks.
- Do not use `#:set` to inject Python globals, callback functions, generated
  text, or state into KV. Set widget properties and bind callbacks from Python
  after loading.

For generated PythonHere cells, do not put Python callbacks in KV.
Do not put generated dynamic Python logic in KV.

Avoid:
`on_release: something()`
`on_press: something()`
`on_text: something(self.text)`
`on_value: something(self.value)`
`values: [f"{num}: {name}" for num, name in sorted(items.items())]`
`text: some_python_variable`
`source: compute_path()`
`angle: app.feature_angle`

Also avoid generated proxy/global calls in KV:
`on_release: actions.handle(...)`
`on_release: app_actions["handle"]()`
`on_release: app.stop_everything()`
`on_release: root.stop_everything()`
`on_release: start_cb()`
`text: app_poem_text`
`#:set start_cb some_python_function`
`#:set app_poem_text some_python_text`

Avoid referencing notebook/global variables from KV. Kivy Builder may not have
the expected globals in parser scope, and KV parser errors are hard to recover
from in a live app. Put dynamic values into widgets from Python after the widget
tree exists.
Do not use `app.some_feature_state` in generated KV. In PythonHere, `app` is the
real PythonHere Kivy App instance, not a generated feature controller. Store
feature state on the generated root/widget class with Kivy properties, or update
widget/canvas instructions from Python.

Preferred pattern:
- Put ids on interactive widgets in KV.
- Load the UI.
- Set dynamic properties from Python after `Builder.load_string(KV)`.
- Bind callbacks in Python after `Builder.load_string(KV)`.

Example:

`ui = Builder.load_string(KV)`
`ui.ids.primary_button.bind(on_release=handle_primary_action)`
`ui.ids.value_slider.bind(value=handle_value_change)`

Dynamic values example:

```
KV = """
BoxLayout:
    Spinner:
        id: instrument_spinner
        text: "Choose instrument"
        values: []
    Slider:
        id: volume_slider
"""

ui = Builder.load_string(KV)
ui.ids.instrument_spinner.values = [
    f"{num}: {name}" for num, name in sorted(midi_instruments.items())
]
ui.ids.instrument_spinner.bind(text=handle_instrument)
ui.ids.volume_slider.bind(value=handle_volume)
```

Widget-owned property example:

```
from kivy.properties import NumericProperty
from kivy.uix.floatlayout import FloatLayout

class DynamicRoot(FloatLayout):
    feature_angle = NumericProperty(0)

KV = """
#:import dp kivy.metrics.dp

<DynamicRoot>:
    canvas.before:
        PushMatrix:
        Rotate:
            angle: root.feature_angle
            origin: self.center
        Ellipse:
            size: dp(120), dp(120)
            pos: self.center_x - dp(60), self.center_y - dp(60)
        PopMatrix:

DynamicRoot:
"""

ui = Builder.load_string(KV)
Clock.schedule_interval(lambda dt: setattr(ui, "feature_angle", ui.feature_angle + 3), 1 / 30)
```

KV root rule:
- In PythonHere generated cells, `KV` must end with a concrete root widget instance.
- Prefer a direct root widget such as `BoxLayout:`, `FloatLayout:`, `GridLayout:`, or a custom class instance such as `DesktopUI:`.
- Do not make `KV` contain only class/rule definitions.
- Do not use KV dynamic class/template syntax such as `<RootWidget@BoxLayout>:`
  for generated PythonHere snippets.
- Do not call `Builder.template(...)`. Use `ui = Builder.load_string(KV)` with a
  KV string that ends in a concrete root widget instance.
- Do not load rule-only KV and then instantiate a Python class manually, such as
  `Builder.load_string(KV); ui = MyWidget()`. The generated KV should return the
  actual root widget from `Builder.load_string(KV)`.
- Do not call `Builder.unload_file(...)` or pass a fake `filename=...` for
  generated inline KV snippets.

Good:

```
KV = """
BoxLayout:
    Label:
        text: "Hello"
"""
```

Good when using custom classes:

```
KV = """
<DesktopUI>:
    ...

DesktopUI:
"""
```

Bad:

```
KV = """
<DesktopUI>:
    ...
"""
```

because `Builder.load_string(KV)` returns `None` for rule-only KV.

Required self-check:
- If the code does `ui = Builder.load_string(KV)`, then `ui` must be a widget.
- If `KV` contains `<SomeClass>:` rules, it must also contain a final concrete instance like `SomeClass:`.
- Never call `root.add_widget(ui)` unless `ui is not None`.
- Never call `Builder.template(...)` for generated PythonHere UI snippets.
- Never define `<SomeName@BaseWidget>:` dynamic classes in generated KV.
- Never use `#:set` to expose Python functions or generated text to KV.
- Never call `Builder.unload_file(...)` for generated inline KV snippets.
- If code defines a `KV = """..."""` string for the UI, it must actually load
  that string with `Builder.load_string(KV)` and add the loaded widget, or omit
  the KV string entirely. Do not define KV and then instantiate a bare Python
  widget class such as `ui = MyWidget()`; that ignores the KV tree and usually
  shows an empty UI.

Kivy property compatibility:
- Generated Kivy code must use only valid property option values in both KV and Python-created widgets. For `Label.shorten_from`, use only `"left"`, `"center"`, or `"right"`.

KV imports:
- Any Python name used inside KV expressions must either be a KV local such as
  `self`, `root`, or an explicitly imported name declared with `#:import` at
  the top of the KV string.
- Do not assume Python imports outside the KV string are visible to the KV
  parser. `from math import sin` in Python does not make `sin(...)` valid inside
  KV; use `#:import sin math.sin` in the KV string or move the calculation into
  Python.
- If KV uses `dp(...)` or `sp(...)`, include exactly one matching import at the
  top of the KV string:
  `#:import dp kivy.metrics.dp`
  `#:import sp kivy.metrics.sp`
- If KV expressions use math functions, include explicit imports such as:
  `#:import sin math.sin`
  `#:import cos math.cos`
- Do not generate duplicate `#:import` lines for the same name.
- Prefer moving nontrivial calculations into Python properties or Python-side
  canvas updates instead of putting complex formulas in KV. This is especially
  important for animated positions, trigonometry, paths, query results, and
  generated lists.
- If a KV canvas expression still uses trigonometry, the KV string must include
  the math imports once, before any widget rules:

```
KV = """
#:import sin math.sin
#:import cos math.cos
#:import dp kivy.metrics.dp

FloatLayout:
    canvas:
        Ellipse:
            size: dp(24), dp(24)
            pos: self.x + self.width * sin(root.phase), self.y
"""
```

- Before returning code, scan the KV string for function calls such as `sin(`,
  `cos(`, `dp(`, `sp(`, `rgba(`, or helper names and ensure each helper is
  defined in KV parser scope or removed.

KV safety additions:
- `ids` exist on the loaded root widget, not as global variables. Access them as
  `ui.ids.some_id` after `Builder.load_string(KV)` returns a concrete root
  widget.
- Avoid assigning duplicate ids in generated KV.
- Do not create dynamic styling aliases such as `<PoemLabel@Label>:`. For
  generated snippets, repeat simple properties, use a real Python class, or set
  properties from Python after loading the widget tree.
- Keep KV expressions literal and simple. Use Python to compute all lists,
  paths, formatted labels, colors derived from runtime state, and callback
  decisions after the widget tree is loaded.
- Do not use `root` in KV to refer to the PythonHere global `root`. In KV,
  `root` means the current KV rule/root widget.
- When a custom root class owns Kivy properties, define the class in Python
  before `Builder.load_string(KV)` and end KV with a concrete instance of that
  class.
