PYTHON_VERSION ?= 3.10
UV_PYTHON := $(PYTHON_VERSION)
export UV_PYTHON

.PHONY: sync test lint format check build venv clean

all: build

sync:
	uv sync --managed-python --group dev

test: sync
	uv run ./run_tests.sh

lint: sync
	uv run ruff check pythonhere tests
	uv run ruff format --check pythonhere tests
	uv run pylint pythonhere

format: sync
	uv run ruff format pythonhere tests

check: lint test

build: clean sync
	uv run python -m build
	uv run twine check dist/*

venv:
	uv venv --python $(PYTHON_VERSION) --managed-python --seed --clear
	uv lock

clean:
	rm -rf .pytest_cache .coverage coverage.xml build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
