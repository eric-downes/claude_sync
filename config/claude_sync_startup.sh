#!/bin/bash
# Claude.ai Chrome Debugging Session Launcher
# This script starts Chrome with remote debugging for Claude.ai project sync

CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT=9222
USER_DATA_DIR="$HOME/.claude-sync-chrome"
LOG_FILE="$HOME/.claude-sync-chrome.log"

# Check if Chrome is already running with debugging
if curl -s http://localhost:$DEBUG_PORT/json/version > /dev/null 2>&1; then
    echo "Chrome debugging session already running on port $DEBUG_PORT"
    exit 0
fi

# Create user data directory if it doesn't exist
mkdir -p "$USER_DATA_DIR"

# Launch Chrome in background with debugging enabled
echo "Starting Chrome with remote debugging on port $DEBUG_PORT..."
nohup "$CHROME_PATH" \
    --remote-debugging-port=$DEBUG_PORT \
    --remote-allow-origins='*' \
    --user-data-dir="$USER_DATA_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --restore-last-session \
    https://claude.ai/projects \
    > "$LOG_FILE" 2>&1 &

echo "Chrome PID: $!"
echo "Log file: $LOG_FILE"

# Wait for Chrome to start
sleep 3

# Check if Chrome started successfully
if curl -s http://localhost:$DEBUG_PORT/json/version > /dev/null 2>&1; then
    echo "Chrome debugging session started successfully!"
    echo "If this is the first run, please:"
    echo "1. Go to the Chrome window that just opened"
    echo "2. Sign in to Claude.ai with your Google account"
    echo "3. Once signed in, the session will persist for future syncs"
else
    echo "Failed to start Chrome debugging session. Check $LOG_FILE for errors."
    exit 1
fi