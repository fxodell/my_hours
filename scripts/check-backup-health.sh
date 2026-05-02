#!/usr/bin/env bash
#
# MyHours backup health audit.
# Runs daily (after backup-db.sh). Checks:
#   1. /opt/myhours/backups/ has at least one dump for each of the last 14 days
#   2. The most recent dump is < 25 hours old
#   3. backup.log and cron.log have no recent ERROR lines
#   4. /etc/cron.d/myhours-backup exists and the cron service is active
#   5. Newest dump passes `gzip -t`
#
# Output: appends one line to /opt/myhours/backups/health.log and writes a
# single-line summary to /opt/myhours/backups/health-status. Exits non-zero
# on any failure so cron will surface it.
#
# Run manually: sudo /opt/myhours/scripts/check-backup-health.sh

set -uo pipefail

BACKUP_DIR="/opt/myhours/backups"
LOG_FILE="${BACKUP_DIR}/health.log"
STATUS_FILE="${BACKUP_DIR}/health-status"
CRON_FILE="/etc/cron.d/myhours-backup"
DAYS_REQUIRED=14
MAX_AGE_HOURS=25

failures=()

# 1. One backup for each of the last 14 days
missing_days=()
for i in $(seq 0 $((DAYS_REQUIRED - 1))); do
    day="$(date -d "-${i} days" +%Y-%m-%d)"
    if ! compgen -G "${BACKUP_DIR}/myhours_${day}_*.sql.gz" > /dev/null; then
        missing_days+=("${day}")
    fi
done
if [ "${#missing_days[@]}" -gt 0 ]; then
    failures+=("missing backups for: ${missing_days[*]}")
fi

# 2. Most recent backup < 25h old
newest=$(find "${BACKUP_DIR}" -maxdepth 1 -name 'myhours_*.sql.gz' -type f -printf '%T@ %p\n' \
         | sort -nr | head -1 | awk '{print $2}')
if [ -z "${newest}" ]; then
    failures+=("no backups exist at all")
else
    age_seconds=$(( $(date +%s) - $(stat -c %Y "${newest}") ))
    age_hours=$(( age_seconds / 3600 ))
    if [ "${age_hours}" -gt "${MAX_AGE_HOURS}" ]; then
        failures+=("newest backup is ${age_hours}h old (>${MAX_AGE_HOURS}h): $(basename "${newest}")")
    fi
fi

# 3. Recent ERROR lines in logs
for log in "${BACKUP_DIR}/backup.log" "${BACKUP_DIR}/cron.log"; do
    if [ -f "${log}" ]; then
        recent_errors=$(tail -50 "${log}" 2>/dev/null | grep -c -i ERROR || true)
        if [ "${recent_errors}" -gt 0 ]; then
            failures+=("${recent_errors} ERROR line(s) in $(basename "${log}") (last 50 lines)")
        fi
    fi
done

# 4. Cron file exists and cron service is active
if [ ! -f "${CRON_FILE}" ]; then
    failures+=("${CRON_FILE} is missing")
fi
if ! systemctl is-active --quiet cron; then
    failures+=("cron service is not active")
fi

# 5. Newest dump passes gzip integrity check
if [ -n "${newest}" ]; then
    if ! gzip -t "${newest}" 2>/dev/null; then
        failures+=("gzip integrity check failed on $(basename "${newest}")")
    fi
fi

now="$(date -Iseconds)"
if [ "${#failures[@]}" -eq 0 ]; then
    summary="OK ${now}: 14d coverage, newest=$(basename "${newest}"), $(du -h "${newest}" | cut -f1)"
    echo "${summary}" >> "${LOG_FILE}"
    echo "${summary}" > "${STATUS_FILE}"
    exit 0
else
    summary="FAIL ${now}: ${#failures[@]} issue(s)"
    {
        echo "${summary}"
        for f in "${failures[@]}"; do
            echo "  - ${f}"
        done
    } | tee -a "${LOG_FILE}"
    echo "${summary}" > "${STATUS_FILE}"
    for f in "${failures[@]}"; do
        echo "  - ${f}" >> "${STATUS_FILE}"
    done
    exit 1
fi
