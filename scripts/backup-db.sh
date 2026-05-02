#!/usr/bin/env bash
#
# MyHours daily PostgreSQL backup.
# Dumps the `myhours` database from the `myhours-db` Docker container,
# gzips it, prunes backups older than 90 days, logs the result.
#
# Run manually: sudo /opt/myhours/scripts/backup-db.sh
# Scheduled by: /etc/cron.d/myhours-backup

set -euo pipefail

CONTAINER="myhours-db"
DB_NAME="myhours"
DB_USER="myhours"
BACKUP_DIR="/opt/myhours/backups"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_DAYS=90

timestamp="$(date +%Y-%m-%d_%H%M%S)"
out_file="${BACKUP_DIR}/myhours_${timestamp}.sql.gz"

log() {
    echo "$(date -Iseconds) $*" >> "${LOG_FILE}"
}

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
    log "ERROR container ${CONTAINER} is not running, aborting"
    exit 1
fi

if ! docker exec "${CONTAINER}" pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --clean --if-exists --no-owner \
    | gzip -9 > "${out_file}"; then
    log "ERROR pg_dump failed, removing partial file ${out_file}"
    rm -f "${out_file}"
    exit 1
fi

if ! gzip -t "${out_file}" 2>/dev/null; then
    log "ERROR gzip integrity check failed for ${out_file}"
    rm -f "${out_file}"
    exit 1
fi

if [ ! -s "${out_file}" ]; then
    log "ERROR backup file is empty: ${out_file}"
    rm -f "${out_file}"
    exit 1
fi

chmod 600 "${out_file}"
size="$(du -h "${out_file}" | cut -f1)"

deleted_count=$(find "${BACKUP_DIR}" -maxdepth 1 -name 'myhours_*.sql.gz' -type f -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)

log "OK ${out_file} (${size}); pruned ${deleted_count} file(s) older than ${RETENTION_DAYS}d"
