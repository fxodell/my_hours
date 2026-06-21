#!/usr/bin/env bash
#
# Ensure weekly pay periods exist for all active companies (groups A and B).
# Idempotent; safe to run daily.
#
# Run manually: sudo /opt/myhours/scripts/generate-pay-periods.sh
# Scheduled by: /etc/cron.d/myhours-pay-periods

set -euo pipefail

ROOT="/opt/myhours"
LOG_DIR="${ROOT}/logs"
LOG_FILE="${LOG_DIR}/pay-periods-cron.log"
CONTAINER="myhours-backend"

log() {
    echo "$(date -Iseconds) $*"
}

mkdir -p "${LOG_DIR}"
chmod 700 "${LOG_DIR}"

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
    log "ERROR container ${CONTAINER} is not running, aborting" >> "${LOG_FILE}"
    exit 1
fi

cd "${ROOT}"

{
    log "Starting pay period generation"
    docker compose exec -T backend python scripts/generate_pay_periods.py
    log "Finished pay period generation"
} >> "${LOG_FILE}" 2>&1
