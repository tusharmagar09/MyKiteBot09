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

# 4. Determine which module to run with Retry Logic
run_with_retries() {
    local script=$1
    local max_attempts=3
    local attempt=1
    local wait_time=120

    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt of $max_attempts for $script..."
        python3 $script
        local exit_code=$?

        if [ $exit_code -eq 0 ]; then
            echo "$script executed successfully."
            return 0
        else
            echo "$script failed with exit code $exit_code."
            if [ $attempt -lt $max_attempts ]; then
                echo "Waiting $wait_time seconds before retrying..."
                sleep $wait_time
            fi
        fi
        attempt=$((attempt + 1))
    done

    echo "All $max_attempts attempts failed for $script."
    local err_msg="🚨 [MoneyFlow] CRITICAL: $script failed after $max_attempts attempts! Server shutting down."
    curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" -d "chat_id=$CHAT_ID" -d "text=$err_msg" > /dev/null
    return 1
}

if [ "$IST_HOUR" -eq 9 ]; then
    echo "Starting Morning Health Check..."
    run_with_retries morning_check.py
elif [ "$IST_HOUR" -eq 15 ]; then
    echo "Starting Evening Trading Scan..."
    run_with_retries live_bot.py
else
    echo "Woke up at unscheduled time ($IST_HOUR IST). Running safety check..."
    run_with_retries morning_check.py
fi

# --- SHUTDOWN PING ---
SHUTDOWN_MSG="🛑 [MoneyFlow] Server Shutting Down. Operations complete."
curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" -d "chat_id=$CHAT_ID" -d "text=$SHUTDOWN_MSG" > /dev/null

echo "Orchestration complete. Shutting down server to save costs and reset for next run..."
sudo shutdown -h now
