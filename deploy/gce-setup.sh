#!/bin/bash
# MyHours GCE Deployment Script
# Run this on a fresh Ubuntu 22.04 VM

set -e

echo "=== MyHours GCE Setup ==="

# Update system
echo "Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Nginx for reverse proxy
echo "Installing Nginx..."
sudo apt-get install -y nginx

# Install Certbot for SSL
echo "Installing Certbot..."
sudo apt-get install -y certbot python3-certbot-nginx

# Create app directory
echo "Creating app directory..."
sudo mkdir -p /opt/myhours
sudo chown $USER:$USER /opt/myhours

echo ""
echo "=== Base setup complete! ==="
echo ""
echo "Next steps:"
echo "1. Log out and back in (for docker group)"
echo "2. Clone your repo: cd /opt/myhours && git clone https://github.com/fxodell/my_hours.git ."
echo "3. Copy and edit .env: cp .env.example .env && nano .env"
echo "4. Run: docker compose up -d"
echo "5. Run migrations: docker compose exec backend alembic upgrade head"
echo "6. Setup SSL: sudo certbot --nginx -d yourdomain.com"
echo ""
