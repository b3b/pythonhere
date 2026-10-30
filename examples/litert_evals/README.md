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

# Benchmarks with Pydantic Evals

Companion notebooks for the [YouTube video](https://youtu.be/CSwZkyGWrhU).

Test a model's Python skills from Jupyter, with inference running locally on
Android through PythonHere. Use Pydantic Evals to run a Python quiz, check
answers, and report results, then build custom evaluators for code-reasoning
tasks and programming challenges. For longer experiments, Task Runner generates
answers in the background on Android so you can fetch and evaluate them later.

## Notebooks

1. [Python quiz](quiz.md)
2. [CruxEval](cruxeval.md)
3. [LeetCode](leetcode.md)

## Resources

- [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/)
- [LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM)
- [Qwen2.5-Coder-3B-Instruct (LiteRT-LM)](https://huggingface.co/litert-community/Qwen2.5-Coder-3B-Instruct)
- [CruxEval dataset](https://huggingface.co/datasets/cruxeval-org/cruxeval)
- [LeetCode dataset](https://huggingface.co/datasets/newfacade/LeetCodeDataset)
