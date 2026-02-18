# MyHours - Google Compute Engine Deployment Guide

## 1. Create the VM Instance

### Via Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Compute Engine** → **VM instances**
3. Click **Create Instance**

### Recommended Settings:

| Setting | Value |
|---------|-------|
| Name | `myhours-prod` |
| Region | `us-central1` (or closest to users) |
| Zone | `us-central1-a` |
| Machine type | `e2-medium` (2 vCPU, 4 GB) |
| Boot disk | Ubuntu 22.04 LTS, 30 GB SSD |
| Firewall | ✅ Allow HTTP, ✅ Allow HTTPS |

### Or via gcloud CLI:

```bash
gcloud compute instances create myhours-prod \
  --machine-type=e2-medium \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-ssd \
  --tags=http-server,https-server
```

## 2. Connect to Your VM

```bash
gcloud compute ssh myhours-prod --zone=us-central1-a
```

## 3. Run Setup Script

```bash
# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/fxodell/my_hours/main/deploy/gce-setup.sh | bash

# Log out and back in (required for docker group)
exit
# SSH back in
gcloud compute ssh myhours-prod --zone=us-central1-a
```

## 4. Deploy the Application

```bash
# Go to app directory
cd /opt/myhours

# Clone the repository
git clone https://github.com/fxodell/my_hours.git .

# Create and configure .env
cp .env.example .env
nano .env
```

### Edit .env with production values:

```env
POSTGRES_USER=myhours
POSTGRES_PASSWORD=<generate-a-strong-password>
POSTGRES_DB=myhours
SECRET_KEY=<generate-a-long-random-string>
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

Generate secure values:
```bash
# Generate random password
openssl rand -base64 32

# Generate secret key
openssl rand -hex 32
```

## 5. Start the Application

```bash
# Build and start containers
docker compose up -d

# Run database migrations
docker compose exec backend alembic upgrade head

# Seed initial data (optional)
docker compose exec backend python scripts/seed_data.py

# Check status
docker compose ps
```

## 6. Configure Domain & SSL

### Point your domain to the VM:
1. Get your VM's external IP: `gcloud compute instances describe myhours-prod --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'`
2. Add an A record in your DNS pointing to this IP

### Setup Nginx reverse proxy:

```bash
# Copy nginx config
sudo cp deploy/nginx-site.conf /etc/nginx/sites-available/myhours

# Edit the domain name
sudo nano /etc/nginx/sites-available/myhours
# Change "your-domain.com" to your actual domain

# Enable the site
sudo ln -s /etc/nginx/sites-available/myhours /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Get SSL certificate:

```bash
sudo certbot --nginx -d your-domain.com
```

## 7. Verify Deployment

1. Visit `https://your-domain.com`
2. Login with admin credentials
3. Test creating a time entry

## Maintenance Commands

```bash
# View logs
docker compose logs -f

# Restart services
docker compose restart

# Update to latest code
cd /opt/myhours
git pull
docker compose build
docker compose up -d

# Backup database
docker compose exec db pg_dump -U myhours myhours > backup_$(date +%Y%m%d).sql

# Restore database
cat backup.sql | docker compose exec -T db psql -U myhours myhours
```

## Troubleshooting

### Check container status:
```bash
docker compose ps
docker compose logs backend
docker compose logs frontend
```

### Check nginx:
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Restart everything:
```bash
docker compose down
docker compose up -d
sudo systemctl restart nginx
```

## Cost Estimate

| Resource | Monthly Cost |
|----------|--------------|
| e2-medium VM | ~$26 |
| 30 GB SSD | ~$3 |
| Egress (minimal) | ~$1 |
| **Total** | **~$30/month** |

Free tier eligible for first 90 days with $300 credit.
