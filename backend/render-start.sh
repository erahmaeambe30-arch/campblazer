#!/usr/bin/env bash
# Render start command. Runs on every boot/restart; every step is safe to repeat.
set -e

# Safety net only: does nothing when the migration files are committed to GitHub (recommended).
python manage.py makemigrations accounts destinations bookings --noinput
python manage.py migrate --noinput     # apply committed migrations (creates/updates tables in PostgreSQL)
python manage.py bootstrap             # seeds ONLY an empty database; never overwrites admin changes

export GUNICORN_BIND="0.0.0.0:${PORT:-8000}"
exec gunicorn -c gunicorn.conf.py config.asgi:application
