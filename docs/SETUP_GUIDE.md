# Claude Sync - Travel-Friendly Setup Guide

## Overview

This tool syncs your Claude.ai projects while traveling, with:
- **Persistent headless Chrome** (~50-80MB idle)
- **Independent Chrome profile** (won't interfere with your browsing)
- **Smart sync conditions** (only on AC power, with internet)
- **Manual 2FA only after reboots**

## Initial Setup

### 1. Install Dependencies

```bash
pip install playwright beautifulsoup4 psutil
playwright install chromium  # One-time Playwright setup
```

### 2. First Run (Manual Auth)

```bash
# This will start headless Chrome and check auth
python persistent_sporadic_sync.py

# When it says "MANUAL AUTHENTICATION REQUIRED", follow the instructions:
# 1. Open the Chrome command it shows you
# 2. Complete Google login + 2FA
# 3. Close that Chrome window
# 4. Press Enter in the terminal
```

### 3. Set Up Cron Job (Optional)

Add to your crontab for automatic syncing:

```bash
crontab -e

# Add this line to try syncing every 2 hours
0 */2 * * * /usr/bin/python3 /path/to/persistent_sporadic_sync.py >> ~/claude-sync.log 2>&1
```

## Daily Usage

### Normal Operation

The script will:
1. Keep Chrome running in the background (~50-80MB)
2. Only sync when conditions are good:
   - ✓ Internet available
   - ✓ On AC power (or battery > 30%)
   - ✓ Not synced in last 2 hours

### After MacBook Restart

You'll need to re-authenticate once:

```bash
python persistent_sporadic_sync.py
# Follow the manual auth steps when prompted
```

### Force Sync

To sync regardless of conditions:

```bash
python persistent_sporadic_sync.py --force
```

### Check Memory Usage

To verify Chrome is staying under 100MB:

```bash
# Monitor existing Chrome
python monitor_chrome_memory.py

# Test headless Chrome memory usage
python monitor_chrome_memory.py --test
```

## Travel Tips

1. **At Hotel/Coffee Shop**: Run `--force` to ensure sync
2. **On the Go**: Let cron handle it - will only sync when plugged in
3. **After Reboot**: Do auth once when you have WiFi + phone for 2FA
4. **Low Memory**: Chrome stays running but under 100MB when idle

## File Locations

- Chrome Profile: `~/.claude-sync-profile/`
- Synced Data: `~/claude-sync-data/`
- Projects: `~/claude-sync-data/projects/`
- State File: `~/claude-sync-data/sync_state.json`

## Troubleshooting

### Chrome using too much memory?

```bash
# Check current usage
ps aux | grep -i chrome | grep claude-sync

# Restart Chrome (will need to re-auth)
pkill -f "user-data-dir.*claude-sync"
python persistent_sporadic_sync.py
```

### Not syncing?

Check conditions:
- Internet: `ping -c 1 8.8.8.8`
- Power: `pmset -g batt`
- Last sync: `cat ~/claude-sync-data/sync_state.json`

### Need to reset everything?

```bash
# Remove all data and start fresh
rm -rf ~/.claude-sync-profile
rm -rf ~/claude-sync-data
python persistent_sporadic_sync.py
```

## How It Works

1. **Persistent Chrome**: Runs headless in background, preserves cookies
2. **Auth Persistence**: Session survives until Chrome is killed/reboot
3. **Low Memory**: Headless + optimization flags = ~50-80MB idle
4. **Smart Sync**: Only runs when conditions are favorable
5. **Manual 2FA**: Only needed after Chrome restarts

This design accepts that 2FA is required after reboots but minimizes how often that happens while keeping memory usage low.