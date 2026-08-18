#!/bin/bash
# ==============================================================================
# Linode (Akamai Cloud) Automated Deployment Script for LinkedIn AI Ghostwriter
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive

echo "======================================================="
echo "🚀 Deploying LinkedIn AI Ghostwriter on Linode..."
echo "======================================================="

APP_DIR="/var/www/ghostwriter"

# 1. Update and install dependencies non-interactively
echo "📦 Installing system dependencies..."
apt-get update -y
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" python3 python3-pip python3-venv curl git ufw

# 2. Setup project directory
echo "📁 Setting up project directory at $APP_DIR ..."
mkdir -p $APP_DIR
cd $APP_DIR

# 3. Create virtual environment and install requirements
echo "🐍 Creating Python Virtual Environment..."
python3 -m venv venv
$APP_DIR/venv/bin/pip install --upgrade pip
$APP_DIR/venv/bin/pip install -r requirements.txt

# 4. Create Systemd Service for 24/7 background execution
echo "⚙️ Creating Systemd background service..."
cat <<EOF > /etc/systemd/system/ghostwriter.service
[Unit]
Description=Daily LinkedIn AI Ghostwriter Streamlit App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=3
EnvironmentFile=-$APP_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

# 5. Reload systemd and start service
systemctl daemon-reload
systemctl enable ghostwriter
systemctl restart ghostwriter

# 6. Configure UFW Firewall if installed
if command -v ufw >/dev/null 2>&1; then
    echo "🛡️ Configuring Firewall..."
    ufw allow 22/tcp || true
    ufw allow 8501/tcp || true
fi

SERVER_IP=$(curl -s ifconfig.me || echo "172.239.109.161")

echo "======================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================================================="
echo "Your app is running 24/7 in the background at:"
echo "👉 http://${SERVER_IP}:8501"
echo ""
echo "Service Commands:"
echo "  - Status:  systemctl status ghostwriter"
echo "  - Restart: systemctl restart ghostwriter"
echo "  - Logs:    journalctl -u ghostwriter -f"
echo "======================================================="
