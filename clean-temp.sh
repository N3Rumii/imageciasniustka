#!/data/data/com.termux/files/usr/bin/bash
# Auto-clean temporary uploads and ffmpeg conversion leftovers

DATA_DIR="/data/data/com.termux/files/home/hosting_cias/data"
TEMP_DIR="$DATA_DIR/temporary-uploads"
STATE_FILE="$DATA_DIR/.clean_temp_state"
LOG_FILE="$DATA_DIR/clean_temp.log"
TMP_DIR="/data/data/com.termux/files/usr/tmp"

# Get real post count from the database
post_count=$(cd /data/data/com.termux/files/home/hosting_cias/server && python3 -c "
from szurubooru import db, model
with db.session() as s:
    print(s.query(model.Post).count())
" 2>/dev/null)

[ -z "$post_count" ] && post_count=0

# Read last cleaned post count
last_cleaned=0
[ -f "$STATE_FILE" ] && last_cleaned=$(cat "$STATE_FILE")

# Clean temporary-uploads when we've crossed a 10-post milestone
target=$(( (post_count / 10) * 10 ))
if [ "$target" -gt "$last_cleaned" ]; then
    temp_count=$(ls "$TEMP_DIR" 2>/dev/null | wc -l)
    if [ "$temp_count" -gt 0 ]; then
        rm -f "$TEMP_DIR"/*
        echo "[$(date)] Cleaned $temp_count temp uploads at post #$post_count (milestone: $target)" >> "$LOG_FILE"
    fi
    echo "$target" > "$STATE_FILE"
fi

# Always clean ffmpeg tmp files older than 1 hour
cleaned_tmp=0
for f in "$TMP_DIR"/tmp*; do
    [ -f "$f" ] || continue
    # Check if file is older than 1 hour (3600 seconds)
    if [ "$(stat -c %Y "$f" 2>/dev/null || echo 0)" -lt "$(($(date +%s) - 3600))" ]; then
        rm -f "$f"
        cleaned_tmp=$((cleaned_tmp + 1))
    fi
done
if [ "$cleaned_tmp" -gt 0 ]; then
    echo "[$(date)] Cleaned $cleaned_tmp stale ffmpeg tmp files" >> "$LOG_FILE"
fi
