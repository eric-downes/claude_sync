# Playwright Claude.ai Access Guide

## Overview
This guide documents the exact steps to get Playwright working with Claude.ai using manual authentication to bypass CAPTCHA issues.

## Prerequisites
- Claude Code with MCP Playwright tools enabled
- Chrome browser installed
- Active Claude.ai account with Google SSO

## Step-by-Step Instructions

### 1. Initial Chrome Launch with Remote Debugging

**Command to run (in terminal):**
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --remote-debugging-port=9222 \
    --remote-allow-origins='*' \
    --user-data-dir=/tmp/chrome-debug-profile \
    --no-first-run \
    --no-default-browser-check \
    https://claude.ai
```

**Critical flags explained:**
- `--remote-debugging-port=9222`: Enables DevTools Protocol access
- `--remote-allow-origins='*'`: **REQUIRED** - Without this, WebSocket connections fail with 403 Forbidden
- `--user-data-dir=/tmp/chrome-debug-profile`: Isolated profile to avoid conflicts
- Target URL: `https://claude.ai`

### 2. Manual Authentication

1. Chrome window opens automatically to claude.ai
2. Click "Sign in with Google" 
3. Complete Google SSO login manually
4. Handle any CAPTCHA challenges
5. Wait until you see your Claude homepage

### 3. Verify Chrome Connection

**In Claude Code, run:**
```python
import requests
response = requests.get('http://localhost:9222/json/version')
print(response.json())
```

**Expected output:**
```json
{
    "Browser": "Chrome/138.0.x.x",
    "Protocol-Version": "1.3",
    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/..."
}
```

### 4. Connect Playwright to Existing Chrome

**In Claude Code:**
```python
# The MCP Playwright tools will automatically connect to the authenticated session
# Just use the navigation commands:
```

**Navigate to projects:**
- Use MCP tool: `mcp__playwright__browser_navigate`
- URL: `https://claude.ai/projects`

**Take snapshot:**
- Use MCP tool: `mcp__playwright__browser_snapshot`

### 5. Access Project Knowledge

**Click on a project:**
```python
# Use the reference ID from the snapshot
# Example: Click "DLPoS" project
mcp__playwright__browser_click(
    element="DLPoS project link",
    ref="e188"  # Use actual ref from snapshot
)
```

**Access knowledge files:**
```python
# Click on a knowledge file
mcp__playwright__browser_click(
    element="2-sided market plan file",
    ref="e747"  # Use actual ref from snapshot
)
```

## Complete Python Script Example

```python
#!/usr/bin/env python3
import json
import requests
from websocket import create_connection
import subprocess
import time
import os

class ClaudePlaywrightAccess:
    def __init__(self, chrome_port=9222):
        self.chrome_port = chrome_port
        self.chrome_url = f"http://localhost:{chrome_port}"
        
    def launch_chrome_if_needed(self):
        """Launch Chrome with debugging if not already running"""
        try:
            response = requests.get(f"{self.chrome_url}/json/version")
            print("Chrome already running with debugging enabled")
            return True
        except:
            print("Launching Chrome with remote debugging...")
            
            chrome_cmd = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "--remote-debugging-port=9222",
                "--remote-allow-origins=*",
                "--user-data-dir=/tmp/chrome-debug-profile",
                "--no-first-run",
                "--no-default-browser-check",
                "https://claude.ai"
            ]
            
            subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)  # Wait for Chrome to start
            
            print("\nIMPORTANT: Please manually sign in to Claude.ai in the Chrome window")
            print("Press Enter when you've completed sign-in...")
            input()
            return True
    
    def get_claude_pages(self):
        """Get all Claude.ai pages from Chrome"""
        response = requests.get(f"{self.chrome_url}/json")
        pages = response.json()
        
        claude_pages = []
        for page in pages:
            if 'claude.ai' in page.get('url', ''):
                claude_pages.append({
                    'title': page.get('title', 'Untitled'),
                    'url': page.get('url'),
                    'ws_url': page.get('webSocketDebuggerUrl')
                })
        
        return claude_pages
    
    def connect_to_page(self, ws_url):
        """Connect to a specific page via WebSocket"""
        return create_connection(ws_url)
    
    def navigate_to_projects(self, ws):
        """Navigate to projects page"""
        ws.send(json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {"url": "https://claude.ai/projects"}
        }))
        time.sleep(3)  # Wait for navigation
    
    def extract_page_content(self, ws):
        """Extract content from current page"""
        # Enable Runtime
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable", "params": {}}))
        
        # Get project list
        js_code = '''
        Array.from(document.querySelectorAll('a[href*="/project/"]')).map(a => ({
            name: a.textContent.trim(),
            url: a.href,
            id: a.href.match(/project\\/([^/?]+)/)?.[1] || 'unknown'
        }))
        '''
        
        ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code}
        }))
        
        # Get response
        while True:
            result = json.loads(ws.recv())
            if result.get('id') == 2:
                if 'result' in result and 'result' in result['result']:
                    return result['result']['result'].get('value', [])

# Usage example
if __name__ == "__main__":
    access = ClaudePlaywrightAccess()
    
    # Ensure Chrome is running
    access.launch_chrome_if_needed()
    
    # Get Claude pages
    pages = access.get_claude_pages()
    print(f"\nFound {len(pages)} Claude.ai pages:")
    for page in pages:
        print(f"  - {page['title']} ({page['url']})")
    
    # Connect to first Claude page
    if pages:
        ws = access.connect_to_page(pages[0]['ws_url'])
        
        # Navigate to projects
        access.navigate_to_projects(ws)
        
        # Extract projects
        projects = access.extract_page_content(ws)
        print(f"\nFound {len(projects)} projects")
        
        ws.close()
```

## Troubleshooting

### Issue: 403 Forbidden on WebSocket connection
**Solution:** Ensure `--remote-allow-origins='*'` flag is used when launching Chrome

### Issue: Chrome won't launch
**Solution:** 
- Check if Chrome is already running: `ps aux | grep "Chrome.*9222"`
- Kill existing process: `pkill -f "Chrome.*remote-debugging-port"`
- Try again

### Issue: Can't find Claude tab
**Solution:**
- Ensure you're signed in
- Check all tabs with: `curl http://localhost:9222/json | jq`
- Look for URLs containing "claude.ai"

### Issue: Playwright MCP tools not connecting
**Solution:**
- The MCP tools connect to their own browser instance
- They maintain session persistence automatically
- Just use the navigation commands directly

## Security Considerations

1. **Local Only**: Chrome debug port only accessible from localhost
2. **Temporary Profile**: Using `/tmp/chrome-debug-profile` for isolation
3. **Manual Auth**: No credentials stored in code
4. **Session Persistence**: Chrome maintains login between sessions

## Automation Script

For automated backup, create `claude_backup.sh`:

```bash
#!/bin/bash
# Check if Chrome is running with debug port
if ! curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
    echo "Starting Chrome with debugging..."
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
        --remote-debugging-port=9222 \
        --remote-allow-origins='*' \
        --user-data-dir="$HOME/.claude-sync-chrome" \
        --no-first-run \
        --no-default-browser-check \
        --restore-last-session \
        https://claude.ai/projects > /dev/null 2>&1 &
    
    sleep 5
    
    if [ ! -f "$HOME/.claude-sync-chrome/Default/Cookies" ]; then
        echo "First run detected. Please sign in to Claude.ai"
        echo "Press Enter when complete..."
        read
    fi
fi

# Run backup script
python3 /path/to/claude_sync.py
```

## Best Practices

1. **Persistent Profile**: Use `$HOME/.claude-sync-chrome` instead of `/tmp` for persistence
2. **Session Check**: Verify authentication before attempting sync
3. **Error Handling**: Always check if operations succeed
4. **Logging**: Log all operations for debugging
5. **Graceful Failures**: Handle network issues and timeouts

This approach provides a reliable fallback when automated authentication fails, leveraging manual sign-in with programmatic access.