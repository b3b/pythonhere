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

# Usage examples

## Before run

Examples in this section use connection settings from the **there.env** file.

**there.env** should be filled with values from the *PythonHere* app Settings section:

```text
# PythonHere device IP address
THERE_HOST=127.0.0.1

# Port, as set in PythonHere app Settings section
THERE_PORT=8022

# Username, as set in PythonHere app Settings section
THERE_USERNAME=here

# Password, as set in PythonHere app Settings section
THERE_PASSWORD=xxx
```

## When using with Docker 

Content of **examples** directory are not preserved.
**work** directory can store data that you want to be kept between runs.
