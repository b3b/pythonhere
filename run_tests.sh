#!/bin/bash

set -e

cd pythonhere
PYTHONPATH=. pytest --cov=. --cov-config=../.coveragerc --cov-report=xml ../tests
coverage report
