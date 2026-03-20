# Production deploy checklist

Use this after pushing backend or frontend changes to the production server (e.g. GCE VM at myhours.nfmconsulting.com).

## Backend code changes (e.g. timesheet sort, API fixes)

1. **On the server**, pull latest code:
   ```bash
   cd /path/to/myhours   # your repo on the VM
   git pull
   ```

2. **Restart the backend** so the new code is loaded:
   ```bash
   ./scripts/production-restart-backend.sh
   ```
   Or manually:
   ```bash
   docker compose restart backend
   ```
   If you get "permission denied" on the Docker socket, run with `sudo` (e.g. `sudo ./scripts/production-restart-backend.sh` or `sudo docker compose restart backend`), or add your user to the `docker` group.

3. **Verify:** Open the Timesheets page; list should be ordered by pay period (newest first), then employee name (A–Z). If you deploy by building a new image (no volume mount of `app/`), run `docker compose build backend && docker compose up -d backend` instead of restart.

## Frontend changes

```bash
cd frontend && npm run build && sudo cp -r dist/* /var/www/html/
```

## Migrations

```bash
docker compose exec backend alembic upgrade head
```
