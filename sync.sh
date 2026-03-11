#!/bin/bash

# 1. Detect Environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    TARGET_DIR="$USERPROFILE/Documents/DataMarketplace"
else
    TARGET_DIR="/var/www/DataMarketplace"
fi

REPO_URL="https://github.com/foreandr/DataMarketplace.git"

# 2. Setup Nested Logging (Year/Month/Day.txt)
YEAR=$(date +%Y)
MONTH=$(date +%m)
DAY=$(date +%d)
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

LOG_DIR="$TARGET_DIR/logs/$YEAR/$MONTH"
LOG_FILE="$LOG_DIR/$DAY.txt"

mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
}

# 3. Execution with Visual Separator
echo "--------------------------------------------------------------------------------" >> "$LOG_FILE"
log "STARTING HOURLY SYNC"

if [ ! -d "$TARGET_DIR" ]; then
    log "[*] Target directory missing. Cloning..."
    git clone "$REPO_URL" "$TARGET_DIR" >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then log "[SUCCESS] Clone complete."; else log "[ERROR] Clone failed."; fi
else
    log "[*] Pulling latest changes..."
    git -C "$TARGET_DIR" pull >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then 
        log "[SUCCESS] Pull complete."
    else 
        log "[ERROR] Pull failed. See details above."
    fi
fi

if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    log "[*] Restarting service..."
    systemctl restart datamarketplace >> "$LOG_FILE" 2>&1
    if [ $? -eq 0 ]; then log "[SUCCESS] Service restarted."; else log "[ERROR] Service restart failed."; fi
fi

log "SYNC FINISHED"
echo "" >> "$LOG_FILE"
echo "Sync complete. Log updated: $LOG_FILE"