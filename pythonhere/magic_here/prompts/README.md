# PythonHere `%%there ai` prompts

These Markdown files are PythonHere-specific prompt sections for `%%there ai`.
They are registered when the `pythonhere` IPython extension is loaded.

The prompt sections describe the live PythonHere runtime: Kivy widgets,
Android/Python-for-Android APIs, Pyjnius, Plyer, runtime permissions, installed
packages, media access, BLE, and MIDI.

## Active by default

Normal `%%there ai` requests use these PythonHere sections together with the
generic [`default`](https://github.com/b3b/herethere/blob/master/herethere/there/ai/prompts/default.md)
prompt from `herethere`:

- [`kivy-runtime`](kivy-runtime.md)
- [`kivy-kv`](kivy-kv.md)
- [`android-runtime`](android-runtime.md)
- [`jnius`](jnius.md)
- [`android-permissions`](android-permissions.md)
- [`android-packages`](android-packages.md)
- [`android-media`](android-media.md)
- [`plyer`](plyer.md)

## Available on request

These sections are registered but not active by default. Add them with
`%%there ai --prompts ...` when a request needs that context:

- [`able`](able.md)
- [`midi`](midi.md)

Example:

```python
%%there ai --prompts able
Build a small BLE scanner prototype.
```

`%%there ai --fix` also uses the `herethere`
[`fix`](https://github.com/b3b/herethere/blob/master/herethere/there/ai/prompts/fix.md)
prompt section.

## Custom prompts

Notebook-specific prompt sections can be added with
`herethere.there.ai.register_ai_prompt(...)`. Use custom prompts for visual
style, domain vocabulary, prototype conventions, or other context that should
not be part of the built-in PythonHere prompt stack.
