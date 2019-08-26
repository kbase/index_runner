#!/bin/sh

set -e

flake8 /app/src
mypy --ignore-missing-imports /app/src
bandit -r /app/src
python -m unittest discover /app/src/test/
