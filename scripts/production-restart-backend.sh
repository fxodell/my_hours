#!/usr/bin/env bash
# Run this on the production server after pulling latest code.
# Restarts the backend container so new Python code (e.g. timesheet sort) is loaded.
# Also re-syncs the backup cron entry so a forgotten install can't silently
# leave the database without nightly backups.
set -e
cd "$(dirname "$0")/.."

echo "Syncing backup cron..."
sudo "$(dirname "$0")/install-backup-cron.sh"

echo "Restarting backend..."
docker compose restart backend
echo "Done. Backend is using the latest code (e.g. timesheet list: pay period desc, then employee name)."
