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

# `%%there ai` examples

## Before run

Examples in this section use connection settings from the **there.env** file.

**there.env** should be filled with values from the *PythonHere* app Settings
section.

`%%there ai` also needs model settings. Put them in **there_ai.env** next to the
notebook:

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
