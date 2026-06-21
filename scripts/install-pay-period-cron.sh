#!/usr/bin/env bash
#
# Install (or refresh) the MyHours pay period generation cron entry.
# Idempotent: prints "up to date" when /etc/cron.d/myhours-pay-periods already
# matches the version-controlled copy; otherwise installs it.
#
# Run manually: sudo /opt/myhours/scripts/install-pay-period-cron.sh
# Also called automatically by scripts/production-restart-backend.sh.

set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/cron/myhours-pay-periods"
DEST="/etc/cron.d/myhours-pay-periods"

if [ ! -f "${SRC}" ]; then
    echo "ERROR source cron file not found: ${SRC}" >&2
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR must run as root (use sudo)" >&2
    exit 1
fi

if [ -f "${DEST}" ] && cmp -s "${SRC}" "${DEST}"; then
    echo "Pay period cron up to date: ${DEST}"
    exit 0
fi

install -m 644 -o root -g root "${SRC}" "${DEST}"
echo "Installed pay period cron: ${DEST}"
