#!/bin/bash
# MoneyFlow — Dynamic Startup Orchestrator
# This script is called automatically when the EC2 starts.

# 1. Get current hour in IST (UTC+5.5)
IST_HOUR=$(date -u -d "+5 hours 30 minutes" +%H)
IST_MINUTE=$(date -u -d "+5 hours 30 minutes" +%M)

echo "Current IST Time: $IST_HOUR:$IST_MINUTE"

# 2. Path to project
PROJECT_DIR="/home/ubuntu/MyKiteBot09/project"
cd $PROJECT_DIR

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
