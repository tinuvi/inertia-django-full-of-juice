#!/usr/bin/env bash
set -e

# Same as start-web.sh, but served by gunicorn's gevent worker instead of
# runserver — the production-like target for the SSR timeout E2E spec.
poetry run python manage.py migrate --noinput
exec poetry run gunicorn -c gunicorn_gevent.py sample.wsgi
