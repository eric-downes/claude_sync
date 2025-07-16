#!/usr/bin/env python3
"""
Working sporadic sync implementation for MacBook travel use.
- Independent Chrome session
- Low memory when idle
- Handles 2FA gracefully
"""
import subprocess
import time
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

try:
    from playwright.sync_api import sync_playwright
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install: pip install playwright beautifulsoup4")
    sys.exit(1)


class SporadicClaudeSync:
    """Sync Claude projects sporadically with minimal resource usage."""
    
    def __init__(self):
        self.profile_dir = Path.home() / ".claude-sync-profile"
        self.data_dir = Path.home() / "claude-sync-data"
        self.state_file = self.data_dir / "sync_state.json"
        self.chrome_process: Optional[subprocess.Popen] = None
        
        # Create directories
        self.profile_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
    
    def start_chrome_headless(self) -> bool:
        """Start Chrome in headless mode (low memory ~50MB)."""
        print("🚀 Starting Chrome in headless mode...")
        
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless",
            "--remote-debugging-port=9222",
            f"--user-data-dir={self.profile_dir}",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-setuid-sandbox",
            "--disable-accelerated-2d-canvas",
            "--disable-background-timer-throttling",
            "--disable-breakpad",
            "--disable-component-extensions-with-background-pages",
            "--disable-extensions",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-ipc-flooding-protection",
            "--disable-renderer-backgrounding",
            "--mute-audio",
            "--no-default-browser-check",
            "--no-first-run",
            "--no-startup-window"
        ]
        
        try:
            self.chrome_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(3)  # Wait for Chrome to start
            return True
        except Exception as e:
            print(f"❌ Failed to start Chrome: {e}")
            return False
    
    def start_chrome_headed(self) -> None:
        """Start Chrome with GUI for authentication."""
        print("\n🔐 Manual authentication required!")
        print("=" * 60)
        print("1. Chrome will open to Claude.ai")
        print("2. Log in with your account")
        print("3. Complete 2FA if prompted")
        print("4. Wait for the projects page to load")
        print("5. Press Enter here when done")
        print("=" * 60)
        
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--remote-debugging-port=9222",
            f"--user-data-dir={self.profile_dir}",
            "--new-window",
            "https://claude.ai/projects"
        ]
        
        subprocess.Popen(cmd)
        input("\nPress Enter after successful login...")
    
    def kill_chrome(self) -> None:
        """Kill Chrome to free memory."""
        if self.chrome_process:
            print("🛑 Stopping Chrome...")
            self.chrome_process.terminate()
            time.sleep(1)
            self.chrome_process = None
        
        # Also kill any orphaned Chrome processes using our profile
        subprocess.run(
            ["pkill", "-f", f"user-data-dir={self.profile_dir}"],
            capture_output=True
        )
    
    def check_auth_valid(self) -> bool:
        """Check if current session can access Claude."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                
                if not context.pages:
                    page = context.new_page()
                else:
                    page = context.pages[0]
                
                # Try to access projects
                page.goto("https://claude.ai/projects", wait_until="domcontentloaded")
                time.sleep(2)
                
                # Check if we're on login page
                if "login" in page.url:
                    return False
                
                # Check if we can see projects
                try:
                    page.wait_for_selector('a[href*="/project/"]', timeout=5000)
                    return True
                except:
                    return False
                    
        except Exception as e:
            print(f"❌ Auth check failed: {e}")
            return False
    
    def extract_and_save_projects(self) -> bool:
        """Extract all projects and save to disk."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()
                
                # Navigate to projects
                page.goto("https://claude.ai/projects")
                page.wait_for_selector('a[href*="/project/"]', timeout=10000)
                
                # Extract all projects
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
                
                # Save each project's knowledge files
                for project in projects:
                    print(f"\n📁 Processing: {project['name']}")
                    
                    # Navigate to project
                    page.goto(project['url'])
                    time.sleep(2)
                    
                    # Get page content
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract knowledge files (simplified for POC)
                    knowledge_files = self._extract_knowledge_files(soup.get_text())
                    
                    # Save project data
                    project_dir = self.data_dir / "projects" / project['id']
                    project_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save project info
                    with open(project_dir / "project.json", "w") as f:
                        json.dump({
                            **project,
                            "files_count": len(knowledge_files),
                            "last_synced": datetime.now().isoformat()
                        }, f, indent=2)
                    
                    # Save file list
                    with open(project_dir / "files.json", "w") as f:
                        json.dump(knowledge_files, f, indent=2)
                    
                    print(f"  ✓ Saved {len(knowledge_files)} files")
                
                # Update sync state
                self._update_sync_state(len(projects))
                return True
                
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return False
    
    def _extract_knowledge_files(self, page_text: str) -> List[Dict[str, any]]:
        """Extract knowledge files from page text."""
        files = []
        
        # Simple extraction based on patterns we've seen
        import re
        
        # Pattern: "filename XXX lines"
        pattern = r'([^\n]+?)\s+(\d+)\s+lines\s+TEXT'
        matches = re.findall(pattern, page_text)
        
        for filename, line_count in matches:
            if 'Select file' not in filename and '%' not in filename:
                files.append({
                    'name': filename.strip(),
                    'lines': int(line_count),
                    'type': 'text'
                })
        
        return files
    
    def _update_sync_state(self, project_count: int) -> None:
        """Update sync state file."""
        state = {
            'last_sync': datetime.now().isoformat(),
            'project_count': project_count,
            'status': 'success'
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def get_last_sync(self) -> Optional[datetime]:
        """Get last successful sync time."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                return datetime.fromisoformat(state['last_sync'])
        return None
    
    def sync_once(self) -> bool:
        """Perform one complete sync cycle."""
        print(f"\n🔄 Claude Sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Check last sync
        last_sync = self.get_last_sync()
        if last_sync:
            hours_ago = (datetime.now() - last_sync).total_seconds() / 3600
            print(f"📅 Last sync: {hours_ago:.1f} hours ago")
        
        try:
            # Start Chrome headless
            if not self.start_chrome_headless():
                return False
            
            # Check auth
            print("🔍 Checking authentication...")
            if not self.check_auth_valid():
                print("❌ Session expired, need manual login")
                self.kill_chrome()
                self.start_chrome_headed()
                self.kill_chrome()
                
                # Restart headless
                if not self.start_chrome_headless():
                    return False
                
                # Verify auth now works
                if not self.check_auth_valid():
                    print("❌ Authentication failed")
                    return False
            
            print("✓ Authentication valid")
            
            # Do the sync
            print("\n📥 Syncing projects...")
            success = self.extract_and_save_projects()
            
            if success:
                print("\n✅ Sync completed successfully!")
            else:
                print("\n❌ Sync failed")
            
            return success
            
        finally:
            # Always cleanup
            self.kill_chrome()
            print("\n💤 Chrome stopped, memory freed")
    
    def sync_if_conditions_good(self) -> bool:
        """Only sync if conditions are favorable."""
        # Check internet
        try:
            subprocess.check_output(
                ["ping", "-c", "1", "-t", "2", "8.8.8.8"],
                stderr=subprocess.DEVNULL
            )
        except:
            print("⚠️  No internet connection, skipping sync")
            return False
        
        # Check if on AC power (MacBook)
        try:
            result = subprocess.check_output(["pmset", "-g", "batt"])
            if b"Battery Power" in result and b"AC Power" not in result:
                print("🔋 On battery power, skipping sync")
                return False
        except:
            pass  # Can't determine, proceed anyway
        
        # Check if recently synced
        last_sync = self.get_last_sync()
        if last_sync:
            hours_since = (datetime.now() - last_sync).total_seconds() / 3600
            if hours_since < 4:  # Don't sync more than every 4 hours
                print(f"⏰ Recently synced ({hours_since:.1f}h ago), skipping")
                return False
        
        # All conditions good
        return self.sync_once()


def main():
    """Main entry point."""
    syncer = SporadicClaudeSync()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        # Force sync regardless of conditions
        print("🔧 Force sync mode")
        return 0 if syncer.sync_once() else 1
    else:
        # Check conditions first
        return 0 if syncer.sync_if_conditions_good() else 1


if __name__ == "__main__":
    sys.exit(main())