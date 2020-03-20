#!/bin/sh

# simpler than the functions below, but not as helpful.
# set -e

exit_on_ready_error() {
    if [ $1 -gt 0 ]
    then
        printf "Error ($1) waiting for index runner to start, exiting tests\n"
        exit 1
    fi
}

exit_on_lint_error() {
    if [ $1 -gt 0 ]
    then
        printf "Error ($1) running linter '$2', exiting tests\n"
        exit 1
    fi
}

# Linters
flake8 /app
exit_on_lint_error $? 'flake8'

mypy --ignore-missing-imports /app
exit_on_lint_error $? 'mypy'

bandit -r /app
exit_on_lint_error $? 'bandit'

# Ensure state file is cleared. It can remain between test runs
# since the container maps the /app directory here.
rm -f /scratch/indexrunner.state

# Start the indexrunner server in the background
python -m src.index_runner.main &

# Monitors the server state file (/app/indexrunner.state), continuing when 
# the server state is "ready".
# The readyness monitor will time out after a given number of seconds.
# Timeout is controlled by the environment variable READY_TIMEOUT, which 
# defaults to 60 seconds.
python scripts/ensure-indexrunner-ready.py
exit_on_ready_error $?

# Run our tests
python -m unittest discover /app/src/test/
