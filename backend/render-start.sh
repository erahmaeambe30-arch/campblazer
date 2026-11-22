#!/usr/bin/env bash
# Render start command. Runs on every boot/restart; every step is safe to repeat.
set -e

# Safety net only: does nothing when the migration files are committed to GitHub (recommended).
python manage.py makemigrations accounts destinations bookings --noinput
python manage.py migrate --noinput     # apply committed migrations (creates/updates tables in PostgreSQL)
python manage.py bootstrap             # seeds ONLY an empty database; never overwrites admin changes

if [ "${RESET_DEMO_ADMIN_PASSWORD:-}" = "true" ]; then
    python manage.py shell -c 'import os; from django.contrib.auth import get_user_model; User=get_user_model(); u=User.objects.get(username="admin_demo"); u.set_password(os.environ["DEMO_PASSWORD"]); u.is_staff=True; u.is_superuser=True; u.save()'
fi

export GUNICORN_BIND="0.0.0.0:${PORT:-8000}"
exec gunicorn -c gunicorn.conf.py config.asgi:application
