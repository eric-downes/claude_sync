# Claude Sync - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers
```bash
playwright install chromium
```

### 3. Start Chrome with DevTools
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

### 4. Log into Claude.ai
In the Chrome window that opened, navigate to https://claude.ai and log in.

### 5. Run Your First Sync
```bash
# Sync all projects
python sync_cli.py sync

# Or sync a specific project
python sync_cli.py sync-project "My Project Name"
```

## What Gets Synced?

```
claude_sync_data/
└── projects/
    └── My-Project-Name/
        ├── project.json      # Project metadata
        └── knowledge/
            ├── document1.txt
            ├── document2.pdf
            └── ...
```

## Common Commands

```bash
# See all your synced projects
python sync_cli.py list

# Sync with custom storage location
python sync_cli.py --storage /path/to/backup sync

# Run in headless mode (no browser window)
python sync_cli.py --headless sync

# Quiet mode (no progress bars)
python sync_cli.py --quiet sync
```

## Tips

- **First sync takes time**: Especially if you have many projects/files
- **Keep Chrome open**: Don't close the Chrome window during sync
- **Check sync status**: Use `list` command to see what's been synced
- **Storage location**: Default is `./claude_sync_data`, use `--storage` to change

## Troubleshooting

**"Chrome not found" error**
- Make sure Chrome is running with the debugging port flag
- Check no other app is using port 9222

**"Not logged in" error**
- Navigate to claude.ai in the Chrome window
- Complete the login process including 2FA if required

**Files not downloading**
- Some files may take longer - the tool retries automatically
- Check the Chrome window isn't showing any popups or prompts

Need more help? Check the full [README.md](README.md) for detailed documentation.