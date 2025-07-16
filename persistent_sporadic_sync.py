#!/usr/bin/env python3
"""
Persistent sporadic sync with low-memory headless Chrome.
- Keeps Chrome running between syncs (avoids repeated 2FA)
- Stays under 100MB when idle
- Manual 2FA coordination when needed
"""
import subprocess
import time
import sys
import os
import json
import psutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

try:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install: pip install playwright beautifulsoup4 psutil")
    sys.exit(1)


class PersistentClaudeSync:
    """Sync Claude projects with persistent headless Chrome."""
    
    def __init__(self):
        self.profile_dir = Path.home() / ".claude-sync-profile"
        self.data_dir = Path.home() / "claude-sync-data"
        self.state_file = self.data_dir / "sync_state.json"
        self.pid_file = self.data_dir / "chrome.pid"
        
        # Create directories
        self.profile_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
    
    def get_chrome_memory_usage(self) -> float:
        """Get Chrome's memory usage in MB."""
        try:
            pid = self.get_chrome_pid()
            if pid:
                process = psutil.Process(pid)
                # Get memory info for process and all children
                memory_mb = process.memory_info().rss / 1024 / 1024
                for child in process.children(recursive=True):
                    memory_mb += child.memory_info().rss / 1024 / 1024
                return memory_mb
        except:
            pass
        return 0
    
    def get_chrome_pid(self) -> Optional[int]:
        """Get Chrome process PID if running."""
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text())
                # Check if process is still running
                if psutil.pid_exists(pid):
                    return pid
            except:
                pass
        return None
    
    def is_chrome_running(self) -> bool:
        """Check if our Chrome instance is running."""
        return self.get_chrome_pid() is not None
    
    def start_chrome_if_needed(self) -> bool:
        """Start Chrome in headless mode if not already running."""
        if self.is_chrome_running():
            memory_mb = self.get_chrome_memory_usage()
            print(f"✓ Chrome already running (using {memory_mb:.1f}MB)")
            return True
        
        print("🚀 Starting persistent headless Chrome...")
        
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless",
            "--remote-debugging-port=9222",
            f"--user-data-dir={self.profile_dir}",
            # Memory optimization flags
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-accelerated-2d-canvas",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-renderer-backgrounding",
            "--aggressive-cache-discard",
            "--aggressive-tab-discard",
            "--disable-component-extensions-with-background-pages",
            "--disable-extensions",
            "--disable-features=OptimizationHints",
            "--disable-features=CalculateNativeWinOcclusion",
            "--enable-features=PartitionAllocGigaCage",
            "--js-flags=--max-old-space-size=128",  # Limit JS heap
            "--max_old_space_size=128",
            "--memory-pressure-off",
            "--mute-audio",
            "--no-default-browser-check",
            "--no-first-run"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Save PID
            self.pid_file.write_text(str(process.pid))
            
            # Wait for Chrome to start
            time.sleep(5)
            
            # Check if it's accessible
            if self._test_chrome_connection():
                memory_mb = self.get_chrome_memory_usage()
                print(f"✓ Chrome started successfully (using {memory_mb:.1f}MB)")
                return True
            else:
                print("❌ Chrome started but not accessible")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start Chrome: {e}")
            return False
    
    def _test_chrome_connection(self) -> bool:
        """Test if we can connect to Chrome."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                return True
        except:
            return False
    
    def check_auth_status(self) -> tuple[bool, str]:
        """
        Check authentication status.
        Returns: (is_authenticated, message)
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                
                # Create or reuse page
                if not context.pages:
                    page = context.new_page()
                else:
                    page = context.pages[0]
                
                # Try to access projects
                print("🔍 Checking authentication...")
                page.goto("https://claude.ai/projects", wait_until="domcontentloaded")
                time.sleep(3)
                
                current_url = page.url
                
                # Check various states
                if "login" in current_url:
                    return False, "Not logged in"
                
                # Try to find projects
                try:
                    page.wait_for_selector('a[href*="/project/"]', timeout=5000)
                    return True, "Authenticated and can see projects"
                except:
                    # Might be on a different page but still authenticated
                    if "claude.ai" in current_url and "login" not in current_url:
                        return True, f"Authenticated but on {current_url}"
                    return False, "Cannot access projects"
                    
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def wait_for_manual_auth(self) -> bool:
        """
        Guide user through manual auth process.
        """
        print("\n" + "🔐 " * 20)
        print("MANUAL AUTHENTICATION REQUIRED")
        print("🔐 " * 20)
        
        print("\nThe headless Chrome needs authentication. Please:")
        print("\n1. Open a new terminal and run:")
        print(f"   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
        print(f"     --user-data-dir={self.profile_dir} \\")
        print(f"     --no-first-run https://claude.ai")
        print("\n2. Complete the Google login flow")
        print("3. Handle 2FA with your phone")
        print("4. Wait until you see your Claude projects")
        print("5. Close that Chrome window")
        print("6. Press Enter here to continue")
        
        print("\n" + "-" * 60)
        input("Press Enter after completing authentication...")
        
        # Verify auth worked
        auth_ok, message = self.check_auth_status()
        if auth_ok:
            print(f"✅ Authentication successful: {message}")
            return True
        else:
            print(f"❌ Authentication failed: {message}")
            return False
    
    def sync_projects(self) -> bool:
        """Perform the actual sync operation."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()
                
                # Navigate to projects
                page.goto("https://claude.ai/projects")
                page.wait_for_selector('a[href*="/project/"]', timeout=10000)
                
                # Extract projects
                projects = page.evaluate("""
                    () => Array.from(document.querySelectorAll('a[href*="/project/"]')).map(link => {
                        const div = link.querySelector('div');
                        if (!div) return null;
                        
                        const children = Array.from(div.children);
                        return {
                            name: children[0]?.textContent?.trim(),
                            description: children[1]?.textContent?.trim(),
                            url: link.href,
                            id: link.href.split('/project/')[1]
                        };
                    }).filter(Boolean)
                """)
                
                print(f"✓ Found {len(projects)} projects")
                
                # Save project data
                summary = []
                for project in projects:
                    project_dir = self.data_dir / "projects" / project['id']
                    project_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save project info
                    with open(project_dir / "project.json", "w") as f:
                        json.dump({
                            **project,
                            "last_synced": datetime.now().isoformat()
                        }, f, indent=2)
                    
                    summary.append(f"  • {project['name']}")
                
                # Update sync state
                self._update_sync_state(len(projects))
                
                # Show summary
                print("\n📁 Synced projects:")
                for item in summary[:10]:  # Show first 10
                    print(item)
                if len(summary) > 10:
                    print(f"  ... and {len(summary) - 10} more")
                
                return True
                
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            return False
    
    def _update_sync_state(self, project_count: int) -> None:
        """Update sync state file."""
        state = {
            'last_sync': datetime.now().isoformat(),
            'project_count': project_count,
            'status': 'success',
            'chrome_pid': self.get_chrome_pid()
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def get_last_sync(self) -> Optional[datetime]:
        """Get last successful sync time."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    return datetime.fromisoformat(state['last_sync'])
            except:
                pass
        return None
    
    def should_sync(self, force: bool = False) -> bool:
        """Check if we should sync based on conditions."""
        if force:
            return True
        
        # Check internet
        try:
            subprocess.check_output(
                ["ping", "-c", "1", "-t", "2", "8.8.8.8"],
                stderr=subprocess.DEVNULL
            )
        except:
            print("⚠️  No internet connection")
            return False
        
        # Check if on battery
        try:
            result = subprocess.check_output(["pmset", "-g", "batt"])
            if b"Battery Power" in result and b"AC Power" not in result:
                # On battery - check percentage
                import re
                match = re.search(rb'(\d+)%', result)
                if match:
                    battery_pct = int(match.group(1))
                    if battery_pct < 30:
                        print(f"🔋 Battery too low ({battery_pct}%)")
                        return False
        except:
            pass
        
        # Check if recently synced
        last_sync = self.get_last_sync()
        if last_sync:
            hours_since = (datetime.now() - last_sync).total_seconds() / 3600
            if hours_since < 2:  # Don't sync more than every 2 hours
                print(f"⏰ Recently synced ({hours_since:.1f}h ago)")
                return False
        
        return True
    
    def run_sync(self, force: bool = False) -> bool:
        """Run a sync cycle."""
        print(f"\n🔄 Claude Sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Check conditions
        if not self.should_sync(force):
            return False
        
        # Start Chrome if needed
        if not self.start_chrome_if_needed():
            return False
        
        # Check auth
        auth_ok, auth_message = self.check_auth_status()
        print(f"   {auth_message}")
        
        if not auth_ok:
            if not self.wait_for_manual_auth():
                return False
        
        # Do sync
        print("\n📥 Syncing projects...")
        success = self.sync_projects()
        
        if success:
            print("\n✅ Sync completed successfully!")
            
            # Report memory usage
            memory_mb = self.get_chrome_memory_usage()
            print(f"💾 Chrome memory usage: {memory_mb:.1f}MB")
            
            if memory_mb > 100:
                print("⚠️  Memory usage higher than expected")
        
        return success


def main():
    """Main entry point."""
    syncer = PersistentClaudeSync()
    
    # Parse args
    force = "--force" in sys.argv
    
    # Show status
    if syncer.is_chrome_running():
        memory_mb = syncer.get_chrome_memory_usage()
        print(f"ℹ️  Chrome is running (using {memory_mb:.1f}MB)")
    else:
        print("ℹ️  Chrome is not running")
    
    # Run sync
    return 0 if syncer.run_sync(force) else 1


if __name__ == "__main__":
    sys.exit(main())