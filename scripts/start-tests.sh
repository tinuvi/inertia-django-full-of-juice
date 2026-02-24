#!/usr/bin/env bash

# https://www.gnu.org/software/bash/manual/bash.html#The-Set-Builtin
# -e  Exit immediately if a command exits with a non-zero status.
# -x Print commands and their arguments as they are executed.
set -e

REPORTS_FOLDER_PATH=tests-reports

# Run the following: docker compose run remote-interpreter bash
PYTHONPATH=. poetry run pytest -v -ra --cov=inertia \
--junitxml=$REPORTS_FOLDER_PATH/junit.xml \
--cov-report=xml:$REPORTS_FOLDER_PATH/coverage.xml \
--cov-report=html:$REPORTS_FOLDER_PATH/html \
--cov-report=term
