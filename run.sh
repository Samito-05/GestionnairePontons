#!/usr/bin/env bash
# Lance le serveur de dev local : http://localhost:8000
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-dev}" DJANGO_DEBUG="${DJANGO_DEBUG:-True}"
python manage.py migrate -v0
python manage.py init_demo >/dev/null 2>&1 || true
exec python manage.py runserver "${@:-8000}"
