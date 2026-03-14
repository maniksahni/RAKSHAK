#!/bin/bash
clear
echo "🛡️  Starting RAKSHAK..."

# Start MySQL if not running
brew services start mysql 2>/dev/null
sleep 1

# Kill any existing Flask on port 5001
lsof -ti :5001 | xargs kill -9 2>/dev/null
pkill -f cloudflared 2>/dev/null
sleep 1

# Create logs dir
mkdir -p ~/Desktop/RAKSHAK/logs
cd ~/Desktop/RAKSHAK

# Start Flask
nohup python3 app.py > logs/server.log 2>&1 &
sleep 3

# Get local IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛡️  RAKSHAK IS LIVE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏠 Localhost : http://localhost:5001"
echo "📱 Network   : http://${LOCAL_IP}:5001"
echo "👤 Admin     : admin@rakshak.com / Admin@123"
echo "👩 User      : priya@example.com / User@123"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
