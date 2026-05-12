#!/bin/bash
# MoneyFlow — Dynamic Startup Orchestrator
# This script is called automatically when the EC2 starts.

# 1. Get current hour in IST (Server timezone is now Asia/Kolkata)
IST_HOUR=$(date +%H)
IST_MINUTE=$(date +%M)

echo "Current IST Time: $IST_HOUR:$IST_MINUTE"

# 2. Path to project
PROJECT_DIR="/home/ubuntu/MyKiteBot09"
cd $PROJECT_DIR

# --- STARTUP PING ---
TOKEN="8648384035:AAH983gcyVl0_PkVtHIpn9vBvjvdkI89ycs"
CHAT_ID="935395132"
MESSAGE="⚡ [MoneyFlow] Server Waking up for $IST_HOUR:$IST_MINUTE check..."
curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" -d "chat_id=$CHAT_ID" -d "text=$MESSAGE" > /dev/null

# 3. Synchronize with latest logic
echo "Updating code from GitHub..."
git pull
cd project

# 3. Determine which module to run
if [ "$IST_HOUR" -eq 9 ]; then
    echo "Starting Morning Health Check..."
    python3 morning_check.py
elif [ "$IST_HOUR" -eq 15 ]; then
    echo "Starting Evening Trading Scan..."
    python3 live_bot.py
else
    echo "Woke up at unscheduled time ($IST_HOUR IST). Running safety check..."
    python3 morning_check.py
fi

echo "Orchestration complete. Shutting down server to save costs and reset for next run..."
sudo shutdown -h now
