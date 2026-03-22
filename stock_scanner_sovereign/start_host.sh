#!/bin/bash
# Solaris Host-Side Start Script
echo "☀️  Starting Solaris Stock Scanner (Host Mode)..."

# 1. Fix permissions if needed
if [ -f "scanner_results.mmap.lock" ]; then
    sudo chown $USER:$USER scanner_results.mmap*
fi

# 2. Setup systemd service if not installed
if [ ! -f "/etc/systemd/system/solaris.service" ]; then
    echo "⚙️ Installing systemd service..."
    sudo cp ../solaris.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable solaris
fi

# 3. Start/Restart the service
sudo systemctl restart solaris

echo "✅ Solaris Scanner is running in the background!"
echo "📡 Dashboard: http://localhost:3000"
echo "🛰️  Sidecar:   http://localhost:3000/breakout"
echo "🔍 Check logs with: journalctl -u solaris -f"
