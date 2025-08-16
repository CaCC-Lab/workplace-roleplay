#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Azure VM Setup for Workplace Roleplay${NC}"

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
sudo apt install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    ufw \
    fail2ban \
    htop

# Setup firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 5000/tcp # Flask (only from localhost)
sudo ufw --force enable

# Create application directory
echo -e "${YELLOW}Creating application directory...${NC}"
mkdir -p /home/ryu/workplace-roleplay

# Setup systemd service
echo -e "${YELLOW}Setting up systemd service...${NC}"
sudo cp /home/ryu/workplace-roleplay/deployment/workplace-roleplay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable workplace-roleplay

# Setup Nginx
echo -e "${YELLOW}Configuring Nginx...${NC}"
sudo cp /home/ryu/workplace-roleplay/deployment/nginx-site.conf /etc/nginx/sites-available/workplace-roleplay
sudo ln -sf /etc/nginx/sites-available/workplace-roleplay /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Setup SSL with Let's Encrypt
echo -e "${YELLOW}Setting up SSL certificate...${NC}"
sudo certbot --nginx -d workplace-roleplay.cacc-lab.net --non-interactive --agree-tos --email admin@cacc-lab.net

# Create environment file template
echo -e "${YELLOW}Creating environment file template...${NC}"
cat > /home/ryu/.env.production << 'EOF'
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=False

# Google API Configuration
GOOGLE_API_KEY=your-google-api-key-here

# Session Configuration
SESSION_TYPE=filesystem
SESSION_FILE_DIR=/home/ryu/workplace-roleplay/flask_session

# Application Settings
LOG_LEVEL=INFO
MAX_CONTENT_LENGTH=10485760  # 10MB
EOF

echo -e "${GREEN}VM setup completed!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit /home/ryu/.env.production with your actual API keys"
echo "2. Add SSH key to GitHub Secrets as AZURE_VM_SSH_KEY"
echo "3. Push to main branch to trigger automatic deployment"
echo "4. Monitor logs with: sudo journalctl -u workplace-roleplay -f"