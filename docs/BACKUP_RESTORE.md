# Database Backup and Restore

## What this is

A nightly `pg_dump` of the production `myhours` database, gzipped to disk on the same VM.

| | |
|---|---|
| **Backup script** | `/opt/myhours/scripts/backup-db.sh` |
| **Audit script** | `/opt/myhours/scripts/check-backup-health.sh` (runs 30 min after backup) |
| **Schedule** | Backup 02:15, audit 02:45 daily, both in `/etc/cron.d/myhours-backup` |
| **Location** | `/opt/myhours/backups/myhours_<YYYY-MM-DD_HHMMSS>.sql.gz` |
| **Retention** | 90 days (older files are deleted automatically each run) |
| **Permissions** | Directory `700`, dump files `600`, owned by `root` (contains hashed passwords + all employee data) |
| **Logs** | `backup.log` (backup script), `health.log` (audit script), `cron.log` (cron stdout/stderr), `health-status` (latest one-line status) |

## Risk warning

Backups live on the **same VM** as the database. They protect against accidental deletes, bad migrations, and corruption — **not** against VM loss, disk failure, or the GCE instance being deleted. Add an offsite copy (GCS) when feasible.

## Manual backup

```bash
sudo /opt/myhours/scripts/backup-db.sh
tail /opt/myhours/backups/backup.log
```

## Check that backups are healthy

The fastest check — read the latest audit verdict:

```bash
sudo cat /opt/myhours/backups/health-status
```

A line starting with `OK` means the audit passed last night. `FAIL` means something is wrong; the same file lists each failed check.

For deeper inspection:

```bash
sudo ls -lh /opt/myhours/backups/myhours_*.sql.gz | tail
sudo tail -20 /opt/myhours/backups/backup.log
sudo tail -20 /opt/myhours/backups/health.log
```

You can also force the audit to run on demand:

```bash
sudo /opt/myhours/scripts/check-backup-health.sh
```

The audit checks: 14 consecutive days of backups exist, the newest is < 25h old, no recent ERROR lines in the logs, the cron file and service are present, and the newest dump passes a gzip integrity check.

## Restore

### Option A: Restore over the live database (destructive)

The dumps are created with `--clean --if-exists`, so they drop and recreate every object before reloading. This wipes whatever is currently in the `myhours` database.

```bash
# Pick the backup you want
ls -lh /opt/myhours/backups/myhours_*.sql.gz

# Restore (replace <timestamp> with the file you picked)
gunzip -c /opt/myhours/backups/myhours_<timestamp>.sql.gz \
  | sudo docker exec -i myhours-db psql -U myhours -d myhours

# Restart the backend so any cached state is cleared
/opt/myhours/scripts/production-restart-backend.sh
```

### Option B: Restore into a scratch database (safe, for inspection)

```bash
sudo docker exec -i myhours-db psql -U myhours -d postgres -c \
  "CREATE DATABASE myhours_restore_test;"

gunzip -c /opt/myhours/backups/myhours_<timestamp>.sql.gz \
  | sudo docker exec -i myhours-db psql -U myhours -d myhours_restore_test

# Inspect
sudo docker exec -it myhours-db psql -U myhours -d myhours_restore_test \
  -c "SELECT COUNT(*) FROM employees;"

# Clean up when done
sudo docker exec -i myhours-db psql -U myhours -d postgres -c \
  "DROP DATABASE myhours_restore_test;"
```

## Disabling or removing

```bash
sudo rm /etc/cron.d/myhours-backup    # Stop the schedule
# Existing dumps in /opt/myhours/backups/ are left in place.
```
