#!/bin/bash

# 1. Detect Environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    echo "[*] Detected Windows Environment"
    TARGET_DIR="$USERPROFILE/Documents/DataMarketplace"
    REPO_URL="https://github.com/foreandr/DataMarketplace.git"
else
    echo "[*] Detected Linux Environment"
    TARGET_DIR="/var/www/DataMarketplace"
    REPO_URL="https://github.com/foreandr/DataMarketplace.git"
fi

# 2. Sync Logic
if [ ! -d "$TARGET_DIR" ]; then
    echo "[*] Target directory not found. Cloning..."
    git clone "$REPO_URL" "$TARGET_DIR"
else
    echo "[*] Target directory exists. Pulling latest changes..."
    git -C "$TARGET_DIR" pull
fi

# 3. Linux-Specific Post-Sync (Restarting your service)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    echo "[*] Restarting DataMarketplace service..."
    systemctl restart datamarketplace
    echo "[+] Service restarted."
fi

echo "[+] Sync complete."