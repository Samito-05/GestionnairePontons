#!/bin/sh
# deploy.sh — pull latest from GitHub and restart
# Usage: ./deploy.sh
# Run from: /share/homes/admin/GestionnairePontons

set -e

REPO="Samito-05/GestionnairePontons"
BRANCH="main"
ZIP_URL="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.zip"
TMP_ZIP="/tmp/gp_deploy.zip"
TMP_DIR="/tmp/gp_deploy"

echo "==> Downloading latest code..."
wget -q -O "$TMP_ZIP" "$ZIP_URL"

echo "==> Extracting..."
rm -rf "$TMP_DIR"
unzip -q "$TMP_ZIP" -d "$TMP_DIR"
SRC="$TMP_DIR/GestionnairePontons-${BRANCH}"

echo "==> Copying files..."
cp -r "$SRC/pontons/"       ./pontons/
cp -r "$SRC/templates/"     ./templates/
cp -r "$SRC/static/"        ./static/
cp -r "$SRC/config/"        ./config/
cp    "$SRC/manage.py"      ./manage.py
cp    "$SRC/requirements.txt" ./requirements.txt
cp    "$SRC/Dockerfile"     ./Dockerfile
cp    "$SRC/docker-compose.yml" ./docker-compose.yml
# .env.production intentionally NOT overwritten

echo "==> Cleaning up..."
rm -rf "$TMP_ZIP" "$TMP_DIR"

echo "==> Restarting web container..."
docker compose restart web

echo "==> Running migrations..."
docker exec $(docker compose ps -q web) python manage.py migrate

echo ""
echo "Deploy complete."
