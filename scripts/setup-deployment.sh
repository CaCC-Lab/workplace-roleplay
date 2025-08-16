#!/bin/bash
"""
🚀 Azure VM Deployment Setup Script
Automated setup for production deployment infrastructure

This script configures:
- System dependencies and security hardening
- Service configurations (systemd, nginx)
- SSL certificates with auto-renewal
- Monitoring and logging
- Deployment user and permissions
"""

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="workplace-app"
APP_USER="ryu"
APP_PATH="/opt/${APP_NAME}"
DOMAIN="workplace-roleplay.cacc-lab.net"
PYTHON_VERSION="3.11"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
}

# Update system packages
update_system() {
    log "🔄 Updating system packages..."
    apt-get update
    apt-get upgrade -y
    apt-get install -y curl wget gnupg2 software-properties-common apt-transport-https
}

# Install Python and dependencies
install_python() {
    log "🐍 Installing Python ${PYTHON_VERSION} and dependencies..."
    
    # Add deadsnakes PPA for latest Python versions
    add-apt-repository ppa:deadsnakes/ppa -y
    apt-get update
    
    apt-get install -y \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip \
        build-essential \
        libffi-dev \
        libssl-dev \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        pkg-config
    
    # Set Python alternatives
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1
    
    # Upgrade pip
    python3 -m pip install --upgrade pip setuptools wheel
}

# Install and configure Nginx
install_nginx() {
    log "🌐 Installing and configuring Nginx..."
    
    apt-get install -y nginx
    
    # Remove default configuration
    rm -f /etc/nginx/sites-enabled/default
    
    # Create nginx user if not exists
    if ! id "nginx" &>/dev/null; then
        useradd --system --shell /bin/false --home /var/cache/nginx nginx
    fi
    
    # Configure nginx security
    cat > /etc/nginx/conf.d/security.conf << 'EOF'
# Security configurations
server_tokens off;
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header X-XSS-Protection "1; mode=block" always;

# Rate limiting
limit_req_zone $binary_remote_addr zone=general:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# Client settings
client_max_body_size 50M;
client_body_timeout 30s;
client_header_timeout 30s;

# Gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_proxied any;
gzip_comp_level 6;
gzip_types
    text/plain
    text/css
    text/xml
    text/javascript
    application/json
    application/javascript
    application/xml+rss
    application/atom+xml
    image/svg+xml;
EOF
    
    # Enable and start nginx
    systemctl enable nginx
    systemctl start nginx
}

# Install Redis
install_redis() {
    log "🔴 Installing and configuring Redis..."
    
    apt-get install -y redis-server
    
    # Configure Redis for security
    sed -i 's/^# requirepass .*/requirepass random_secure_password/' /etc/redis/redis.conf
    sed -i 's/^bind 127.0.0.1/bind 127.0.0.1/' /etc/redis/redis.conf
    sed -i 's/^# maxmemory .*/maxmemory 256mb/' /etc/redis/redis.conf
    sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
    
    systemctl enable redis-server
    systemctl restart redis-server
}

# Install SSL certificate with Let's Encrypt
install_ssl() {
    log "🔒 Installing SSL certificate with Let's Encrypt..."
    
    # Install certbot
    apt-get install -y snapd
    snap install core; snap refresh core
    snap install --classic certbot
    
    # Create symlink
    ln -sf /snap/bin/certbot /usr/bin/certbot
    
    # Stop nginx temporarily
    systemctl stop nginx
    
    # Obtain certificate
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email admin@${DOMAIN} \
        --domains ${DOMAIN}
    
    # Set up auto-renewal
    cat > /etc/cron.d/certbot << EOF
0 12 * * * root /usr/bin/certbot renew --quiet && systemctl reload nginx
EOF
    
    # Start nginx
    systemctl start nginx
}

# Create application user and directories
setup_app_user() {
    log "👤 Setting up application user and directories..."
    
    # Create app user if not exists
    if ! id "$APP_USER" &>/dev/null; then
        useradd --system --shell /bin/bash --home /home/$APP_USER --create-home $APP_USER
    fi
    
    # Create application directories
    mkdir -p $APP_PATH/{releases,shared/{logs,uploads}}
    
    # Set permissions
    chown -R $APP_USER:$APP_USER $APP_PATH
    chmod -R 755 $APP_PATH
    
    # Create logs directories
    mkdir -p /var/log/nginx
    chown nginx:nginx /var/log/nginx
    
    # Setup sudo access for service management
    cat > /etc/sudoers.d/$APP_USER << EOF
$APP_USER ALL=(ALL) NOPASSWD: /bin/systemctl reload $APP_NAME, /bin/systemctl restart $APP_NAME, /bin/systemctl start $APP_NAME, /bin/systemctl stop $APP_NAME, /bin/systemctl status $APP_NAME
EOF
}

# Install monitoring tools
install_monitoring() {
    log "📊 Installing monitoring and logging tools..."
    
    # Install system monitoring tools
    apt-get install -y htop iotop nethogs ncdu tree fail2ban
    
    # Configure fail2ban for SSH protection
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF
    
    systemctl enable fail2ban
    systemctl start fail2ban
    
    # Install log rotation
    cat > /etc/logrotate.d/$APP_NAME << EOF
$APP_PATH/shared/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        systemctl reload $APP_NAME
    endscript
}
EOF
}

# Configure firewall
setup_firewall() {
    log "🔥 Configuring firewall..."
    
    # Install and configure UFW
    apt-get install -y ufw
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow specific services
    ufw allow ssh
    ufw allow 'Nginx Full'
    
    # Rate limiting for SSH
    ufw limit ssh
    
    # Enable firewall
    echo "y" | ufw enable
}

# System hardening
system_hardening() {
    log "🛡️ Applying system hardening..."
    
    # Disable unnecessary services
    systemctl disable --now avahi-daemon || true
    systemctl disable --now cups || true
    systemctl disable --now bluetooth || true
    
    # Configure SSH hardening
    sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    sed -i 's/#AuthorizedKeysFile/AuthorizedKeysFile/' /etc/ssh/sshd_config
    
    # Add SSH hardening
    cat >> /etc/ssh/sshd_config << 'EOF'

# Security hardening
Protocol 2
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
MaxStartups 10:30:100
AllowGroups ssh-users
X11Forwarding no
PrintMotd no
TCPKeepAlive no
Compression no
AllowAgentForwarding no
AllowTcpForwarding no
PermitTunnel no
EOF
    
    # Create SSH users group
    groupadd -f ssh-users
    usermod -a -G ssh-users $APP_USER
    
    # Restart SSH
    systemctl restart ssh
    
    # Set kernel parameters
    cat > /etc/sysctl.d/99-security.conf << 'EOF'
# Network security
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
EOF
    
    sysctl -p /etc/sysctl.d/99-security.conf
}

# Install deployment tools
install_deployment_tools() {
    log "🛠️ Installing deployment tools..."
    
    # Install required packages for deployment
    apt-get install -y rsync git jq bc
    
    # Install Azure CLI
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash
    
    # Install Python packages for health checking
    python3 -m pip install psutil aiohttp asyncssh pydantic
}

# Create systemd service template
create_service_template() {
    log "⚙️ Creating systemd service template..."
    
    cat > /etc/systemd/system/$APP_NAME.service << EOF
[Unit]
Description=Workplace Roleplay Flask Application
Documentation=https://github.com/CaCC-Lab/workplace-roleplay
After=network.target redis.service
Wants=redis.service

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_PATH/current
Environment=PATH=$APP_PATH/current/venv/bin
EnvironmentFile=$APP_PATH/current/.env
ExecStart=$APP_PATH/current/venv/bin/gunicorn \\
    --bind 0.0.0.0:5000 \\
    --workers 2 \\
    --worker-class gevent \\
    --worker-connections 1000 \\
    --max-requests 1000 \\
    --max-requests-jitter 50 \\
    --timeout 30 \\
    --keep-alive 2 \\
    --log-level info \\
    --access-logfile $APP_PATH/shared/logs/access.log \\
    --error-logfile $APP_PATH/shared/logs/error.log \\
    --capture-output \\
    --enable-stdio-inheritance \\
    app:app

ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_PATH/shared/logs $APP_PATH/shared/uploads
NoNewPrivileges=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
MemoryHigh=512M
MemoryMax=1G
CPUQuota=200%

# Monitoring and health
WatchdogSec=30
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable $APP_NAME
}

# Final system configuration
final_configuration() {
    log "🔧 Applying final configuration..."
    
    # Create health check endpoint
    mkdir -p /usr/local/bin
    cat > /usr/local/bin/health-check << 'EOF'
#!/bin/bash
python3 /opt/workplace-app/current/scripts/health_check.py --exit-code
EOF
    chmod +x /usr/local/bin/health-check
    
    # Create deployment status file
    cat > $APP_PATH/deployment-status.json << EOF
{
    "setup_completed": "$(date -Iseconds)",
    "version": "1.0.0",
    "components": {
        "nginx": "installed",
        "redis": "installed",
        "ssl": "configured",
        "monitoring": "installed",
        "firewall": "configured",
        "systemd": "configured"
    }
}
EOF
    
    chown $APP_USER:$APP_USER $APP_PATH/deployment-status.json
}

# Main execution
main() {
    log "🚀 Starting Azure VM deployment setup for $APP_NAME"
    
    check_root
    update_system
    install_python
    install_nginx
    install_redis
    setup_app_user
    install_ssl
    install_monitoring
    setup_firewall
    system_hardening
    install_deployment_tools
    create_service_template
    final_configuration
    
    log "✅ Deployment setup completed successfully!"
    log "📋 Next steps:"
    log "   1. Configure GitHub repository secrets"
    log "   2. Set up Azure Key Vault with application secrets"
    log "   3. Run initial deployment from GitHub Actions"
    log "   4. Verify application health at https://$DOMAIN/health"
    
    warn "🔐 Remember to:"
    warn "   - Add your SSH public key to /home/$APP_USER/.ssh/authorized_keys"
    warn "   - Configure Azure Key Vault with GOOGLE_API_KEY and FLASK_SECRET_KEY"
    warn "   - Test deployment script before production use"
}

# Run main function
main "$@"