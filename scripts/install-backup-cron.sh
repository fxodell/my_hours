#!/usr/bin/env bash
#
# Install (or refresh) the MyHours backup cron entry.
# Idempotent: prints "up to date" when /etc/cron.d/myhours-backup already
# matches the version-controlled copy; otherwise installs it.
#
# Run manually: sudo /opt/myhours/scripts/install-backup-cron.sh
# Also called automatically by scripts/production-restart-backend.sh.

set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/cron/myhours-backup"
DEST="/etc/cron.d/myhours-backup"

if [ ! -f "${SRC}" ]; then
    echo "ERROR source cron file not found: ${SRC}" >&2
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR must run as root (use sudo)" >&2
    exit 1
fi

if [ -f "${DEST}" ] && cmp -s "${SRC}" "${DEST}"; then
    echo "Backup cron up to date: ${DEST}"
    exit 0
fi

install -m 644 -o root -g root "${SRC}" "${DEST}"
echo "Installed backup cron: ${DEST}"
