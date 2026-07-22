#!/data/data/com.termux/files/usr/bin/bash
# Watchdog: runs clean-temp.sh every 10 minutes

SCRIPT_DIR="/data/data/com.termux/files/home/hosting_cias"
LOG="$SCRIPT_DIR/data/clean_temp.log"

echo "[$(date)] Watchdog started" >> "$LOG"

while true; do
    "$SCRIPT_DIR/clean-temp.sh"
    sleep 600
done
