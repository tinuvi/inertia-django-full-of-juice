#!/usr/bin/env bash
set -e

# poetry.toml pins an in-project virtualenv, so run through poetry.
poetry run python manage.py migrate --noinput
exec poetry run python manage.py runserver 0.0.0.0:8000
