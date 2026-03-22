#!/bin/bash
# Solaris Start Script
echo "☀️  Starting Solaris Stock Scanner Suite..."

# 1. Fix permissions if needed
if [ -f "stock_scanner_sovereign/scanner_results.mmap.lock" ]; then
    sudo chown $USER:$USER stock_scanner_sovereign/scanner_results.mmap*
fi

# 2. Start the stack
docker-compose up --build -d

echo "✅ Solaris is running!"
echo "📡 Dashboard: http://localhost:3000"
echo "🛰️  Sidecar:   http://localhost:3000/breakout"
