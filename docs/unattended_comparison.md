# Unattended Operation: Current vs Playwright Approach

## Current Approach Challenges

1. **Fragile WebSocket Connection**
   ```python
   # Current: Manual WebSocket that drops
   self._ws = create_connection(ws_url)
   # No automatic reconnection
   ```

2. **Manual Wait Times**
   ```python
   time.sleep(3)  # Hope it's enough
   ```

3. **Complex Auth Handling**
   ```python
   # Need to detect login page, handle redirects, etc.
   if "/login" in current_url:
       # Complex auth flow
   ```

## Playwright + CDP Solution

### Key Insight: Reuse Existing Browser Session

1. **One-Time Manual Setup**
   ```bash
   # You do this ONCE:
   1. Launch Chrome with --remote-debugging-port=9222
   2. Log into Claude.ai manually
   3. Keep Chrome running
   ```

2. **Playwright Connects to Authenticated Session**
   ```python
   # Playwright connects to YOUR Chrome with YOUR cookies
   browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
   page = browser.contexts[0].pages[0]  # Already logged in!
   ```

3. **Unattended Operation**
   ```python
   # Run every hour, day, etc. - no manual intervention
   while True:
       extract_all_projects()  # Works because auth is preserved
       time.sleep(3600)        # Run hourly
   ```

## Why This Works for Unattended Operation

1. **No Auth in Code**: The browser keeps you logged in
2. **Reliable Connection**: Playwright handles reconnections
3. **Smart Waiting**: `page.wait_for_selector()` vs `time.sleep()`
4. **Session Persistence**: Chrome keeps cookies between script runs

## Minimal Unattended Script

```python
# unattended_sync.py
from playwright.sync_api import sync_playwright
import schedule
import time

def sync_claude_projects():
    """Runs unattended - no manual intervention needed."""
    with sync_playwright() as p:
        # Connect to already-authenticated Chrome
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        
        # Do your sync - auth is already handled!
        page.goto("https://claude.ai/projects")
        # ... extract and save data ...

# Schedule to run every hour
schedule.every(1).hours.do(sync_claude_projects)

# Run forever unattended
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Setup Once, Run Forever

1. **Initial Setup** (you do this once):
   ```bash
   # Launch Chrome
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --user-data-dir=~/.claude-sync-profile
   
   # Manually log into Claude.ai
   # Close the terminal but keep Chrome running
   ```

2. **Run Sync Script**:
   ```bash
   # Runs unattended forever
   python unattended_sync.py &
   ```

3. **It Just Works**: 
   - No auth prompts
   - Survives Chrome restarts (cookies persist)
   - Handles connection drops gracefully

## The Key Advantages

1. **Auth Simplicity**: Let Chrome handle it, not your code
2. **Reliability**: Playwright's battle-tested connection handling
3. **Maintenance**: Update CSS selectors, not WebSocket protocols
4. **Debugging**: Can watch the browser when needed

This approach separates concerns:
- Chrome handles: Auth, cookies, sessions
- Your script handles: Data extraction, storage
- Playwright handles: Connection reliability