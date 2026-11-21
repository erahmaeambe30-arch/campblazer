#!/usr/bin/env bash
# Render build command (runs from the repository root). One web service:
#   1. install the Django backend, 2. compile the React + TypeScript frontend,
#   3. collect Django's static files. Django then serves API + frontend + photos.
set -e

pip install --upgrade pip
pip install -r backend/requirements.txt

cd frontend
npm ci || npm install
npm run build              # -> frontend/dist (served by WhiteNoise at "/")
cd ../backend

python manage.py collectstatic --noinput
