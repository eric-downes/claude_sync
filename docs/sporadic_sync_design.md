# Sporadic Sync Design for MacBook Travel Use

## The 2FA Challenge

You've identified the core issue: Claude requires 2FA after browser restarts. This is by design and can't be bypassed. However, we can work WITH this constraint.

## Solution: Hybrid Approach

### 1. Independent Chrome Profile (Headless)
```bash
# Create dedicated profile that runs headless when not needed
CLAUDE_PROFILE="$HOME/.claude-sync-profile"

# Run headless most of the time (low memory ~50MB)
google-chrome --headless --remote-debugging-port=9222 \
  --user-data-dir="$CLAUDE_PROFILE" \
  --disable-gpu --no-sandbox

# When you need to auth, temporarily run with head
google-chrome --remote-debugging-port=9222 \
  --user-data-dir="$CLAUDE_PROFILE"
```

### 2. Smart Session Management

```python
class ClaudeSyncSession:
    def __init__(self):
        self.profile_dir = Path.home() / ".claude-sync-profile"
        self.last_sync = self.load_last_sync()
        self.session_valid = False
    
    def check_session_validity(self):
        """Check if we can access Claude without 2FA."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                page = browser.contexts[0].pages[0]
                page.goto("https://claude.ai/projects", timeout=10000)
                
                # Check if redirected to login
                if "login" in page.url:
                    return False
                    
                # Try to find projects
                projects = page.query_selector_all('a[href*="/project/"]')
                return len(projects) > 0
        except:
            return False
    
    def needs_reauth(self):
        """Determine if we need manual reauth."""
        # Check various conditions
        if not self.profile_exists():
            return True
        if not self.chrome_running():
            return True
        if not self.check_session_validity():
            return True
        return False
```

### 3. Sporadic Sync Workflow

```python
# sporadic_sync.py
import subprocess
import time
from pathlib import Path

class SporadicClaudeSync:
    def __init__(self):
        self.chrome_process = None
        self.profile_dir = Path.home() / ".claude-sync-profile"
    
    def start_chrome_headless(self):
        """Start Chrome in headless mode (low memory)."""
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless",
            "--remote-debugging-port=9222",
            f"--user-data-dir={self.profile_dir}",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",  # Reduce memory
            "--disable-web-security",   # Avoid CORS issues
            "--disable-features=VizDisplayCompositor"
        ]
        self.chrome_process = subprocess.Popen(cmd, 
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)
        time.sleep(3)
    
    def start_chrome_headed(self):
        """Start Chrome with GUI for auth."""
        print("🔐 Manual authentication required!")
        print("1. Chrome will open")
        print("2. Log into Claude.ai")
        print("3. Complete 2FA")
        print("4. Press Enter when done")
        
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--remote-debugging-port=9222",
            f"--user-data-dir={self.profile_dir}",
            "--new-window",
            "https://claude.ai"
        ]
        subprocess.Popen(cmd)
        input("\nPress Enter after logging in...")
    
    def sync_once(self):
        """Perform one sync operation."""
        # Start headless Chrome
        self.start_chrome_headless()
        
        try:
            # Check if auth is valid
            if not self.check_auth_valid():
                print("❌ Session expired, need reauth")
                self.kill_chrome()
                self.start_chrome_headed()
                self.kill_chrome()
                self.start_chrome_headless()
            
            # Do the sync
            print("✓ Syncing...")
            self.extract_all_projects()
            print("✓ Sync complete")
            
        finally:
            # Always kill Chrome to save memory
            self.kill_chrome()
    
    def kill_chrome(self):
        """Kill Chrome to free memory."""
        if self.chrome_process:
            self.chrome_process.terminate()
            time.sleep(1)
```

## Usage Patterns for Travel

### 1. Morning Sync (Manual)
```bash
# Run when you have internet at hotel/cafe
python sporadic_sync.py

# It will:
# 1. Start Chrome headless
# 2. Check if auth valid
# 3. If not, open Chrome for you to do 2FA
# 4. Sync all projects
# 5. Kill Chrome (frees memory)
```

### 2. Opportunistic Sync Script
```python
# opportunity_sync.py
import subprocess
import time

def has_internet():
    """Check if we have internet."""
    try:
        subprocess.check_output(["ping", "-c", "1", "8.8.8.8"])
        return True
    except:
        return False

def on_ac_power():
    """Check if on AC power (MacBook)."""
    result = subprocess.check_output(["pmset", "-g", "batt"])
    return b"AC Power" in result

def should_sync():
    """Sync only when conditions are good."""
    return has_internet() and on_ac_power()

# Run opportunistically
if should_sync():
    print("Good conditions, syncing...")
    subprocess.run(["python", "sporadic_sync.py"])
else:
    print("Skipping sync (no internet or on battery)")
```

### 3. LaunchAgent for Sporadic Sync
```xml
<!-- ~/Library/LaunchAgents/com.claude.sporadic-sync.plist -->
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.sporadic-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/eric/claude_sync/opportunity_sync.py</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer> <!-- Try every hour -->
    <key>RunAtLoad</key>
    <false/>
    <key>Nice</key>
    <integer>10</integer> <!-- Low priority -->
</dict>
</plist>
```

## Key Benefits

1. **Independent Chrome**: Dedicated profile, won't interfere with your browsing
2. **Low Memory**: Headless mode uses ~50MB, killed after sync
3. **2FA Friendly**: Prompts for reauth when needed
4. **Travel Friendly**: Only syncs when conditions are good
5. **Containerizable**: Can package headless Chrome + script in Docker

## The 2FA Reality

We can't avoid 2FA after restarts, but we can:
1. Minimize how often it's needed (persistent profile)
2. Make reauth painless (automated detection + prompt)
3. Run efficiently between reauths (headless, low memory)
4. Handle sporadic connectivity gracefully

Would you like me to create a working implementation of this approach?