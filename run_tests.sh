#!/bin/bash

set -e

cd pythonhere
if [ "$#" -eq 0 ]; then
    set -- ../tests
fi
PYTHONPATH=. xvfb-run --auto-servernum pytest --cov=. --cov-config=../.coveragerc --cov-report=xml "$@"
coverage report -i
