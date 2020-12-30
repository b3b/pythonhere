---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.2'
      jupytext_version: 1.7.1
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# Getting started with <span style="color:#306998">Python</span><span style="color:#FFD43B">Here</span>


## Load the extension, and connect to the remote instance

```python
%load_ext pythonhere
%connect-there
```

## Execute some code on the remote

```python
%%there
from kivy import platform
print("Hello from", platform)
```

## Use Kivy widgets

```python
%%there
from kivy.uix.label import Label

# Kivy's root widget is available via the `root` variable.
root.clear_widgets()  # Remove all current childrens

# And add the new one
widget = Label(text="Kivy", font_size="50sp")
root.add_widget(widget)
```

```python
%there screenshot -w 400
```

## Objects introspection

```python
%%there
print(root.children)
print(widget.color)
```

## Modify widget properties

```python
%%there
widget.color = [1, .5, 0, 1]
widget.text += " Rocks!"
```

```python
%there screenshot -w 400
```

## Make things dynamic with  [Clock](https://kivy.org/doc/stable/api-kivy.clock.html)

```python
%%there
from kivy.clock import Clock

def clock_callback(delta_time):
    widget.color[1] = (widget.color[1] + .1) % 1

clock = Clock.schedule_interval(clock_callback, 0.2)
```

```python
%there -d .5 screenshot -w 400
```

```python
%%there
Clock.unschedule(clock)
```

## Use platform specific features with [Plyer](https://github.com/kivy/plyer)

```python
%%there
from plyer import tts
tts.speak("yo" * 10)
```

## Declare interface with the [KV](https://kivy.org/doc/stable/guide/lang.html) language

```python
%%there kv
Button:
    text: "Click me"
    font_size: 10
    on_release: self.font_size += 1
```

```python
%there -d 5 screenshot -w 400
```

## Combine Python with KV

```python
%%there
from plyer import vibrator
from kivy.uix.button import Button

class VibroClone(Button):

    def on_release(self):
        self.root.add_widget(
            VibroClone(root=self.root)
        )
        vibrator.vibrate(0.05 * int(self.text))

root.clear_widgets()
```

```python
%%there kv
#:import get_random_color kivy.utils.get_random_color
#:import random random

<VibroClone>:
    text: str(random.randint(1, 9))
    color: get_random_color()
    background_color: get_random_color()
    size_hint: 1, 1

GridLayout:
    cols: 10
    size_hint: 1, 1
    VibroClone:
        root: root
```

```python
%there -d 4 screenshot -w 400
```
