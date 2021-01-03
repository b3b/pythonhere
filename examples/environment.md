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

# Execution environment

```python
%load_ext pythonhere
%connect-there
```

Commands are executed in the application main thread, thread is blocked until the end of a cell code execution.<br>
On first SSH connection, BoxLayout is set as a root widget.

Variables in the scope of the *%there* command:
* **app** - Kivy application instance
* **root** - current root widget

```python
%%there
print(app)
print(root)
```

## KV rules
*%there kv* rules processing is different from the normal Kivy behavior.<br>
When class is registered for second time with the same name, previous declaration for that class is deleted.

```python
%%there kv
<MyButton@Button>:
    color: "orange"
    text: "Orange"
        
MyButton:
    font_size: 100
```

```python
%there screenshot -w 200
```

```python
%%there kv
<MyButton@Button>:
    text: "Orange?"
        
MyButton:
    font_size: 100
```

`color: "orange"` rule is removed:

```python
%there screenshot -w 200
```
