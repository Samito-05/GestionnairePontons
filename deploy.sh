#!/bin/sh
# deploy.sh — git pull latest and restart
# Usage: sh deploy.sh
# Run from: /share/homes/admin/GestionnairePontons
#
# Uses a throwaway Docker container to run git, since the NAS host
# has no git binary installed. Requires this directory to already
# be a git clone (contains .git/).

set -e

echo "==> Pulling latest code..."
docker run --rm -v "$(pwd):/repo" -w /repo alpine/git pull origin main
# .env.production is gitignored — never touched by this pull

echo "==> Rebuilding and restarting..."
docker compose up -d --build

echo "==> Waiting for web container to be ready..."
sleep 5

echo "==> Running migrations..."
docker compose exec web python manage.py migrate

echo ""
echo "Deploy complete."
