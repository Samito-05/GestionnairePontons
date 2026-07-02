#!/bin/sh
# backup.sh — dump the database to a timestamped JSON file
# Usage: sh backup.sh
# Run from: /share/homes/admin/GestionnairePontons
# Schedule (QNAP): crontab -e → add:
#   0 3 * * * cd /share/homes/admin/GestionnairePontons && sh backup.sh >> backups/backup.log 2>&1

set -e

BACKUP_DIR="./backups"
KEEP=30

mkdir -p "$BACKUP_DIR"

STAMP=$(date +%Y%m%d_%H%M)
FILE="$BACKUP_DIR/backup_${STAMP}.json"

echo "==> Dumping database to $FILE"
docker compose exec -T web python manage.py dumpdata \
    --exclude contenttypes --exclude auth.permission --exclude axes \
    > "$FILE"

echo "==> Pruning old backups (keeping last $KEEP)"
ls -1t "$BACKUP_DIR"/backup_*.json 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
    rm -f "$old"
done

echo "Backup done: $FILE ($(wc -c < "$FILE") bytes)"
