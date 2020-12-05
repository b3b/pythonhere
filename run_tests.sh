#!/bin/bash

set -e

cd pythonhere
PYTHONPATH=. xvfb-run --auto-servernum pytest --cov=. --cov-config=../.coveragerc --cov-report=xml ../tests
coverage report
