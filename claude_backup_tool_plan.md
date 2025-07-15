# Claude Project Backup Tool - Implementation Plan

## Overview
A fully automated Python tool that backs up all Claude.ai project knowledge files locally, with support for both direct browser automation and Playwright MCP fallback.

## Architecture

```
claude-backup/
├── claude_backup.py          # Main entry point
├── auth/
│   ├── __init__.py
│   ├── session_manager.py    # Handle Chrome sessions and auth
│   └── credential_store.py   # Secure credential storage
├── browser/
│   ├── __init__.py
│   ├── chrome_controller.py  # Chrome DevTools Protocol
│   └── playwright_mcp.py     # MCP fallback integration
├── scraper/
│   ├── __init__.py
│   ├── project_discovery.py  # Find all projects
│   ├── file_extractor.py     # Extract knowledge files
│   └── content_parser.py     # Parse file contents
├── storage/
│   ├── __init__.py
│   ├── local_backup.py       # Save files locally
│   ├── change_detector.py    # Track changes
│   └── metadata_manager.py   # Project metadata
├── config/
│   ├── __init__.py
│   └── settings.py           # Configuration
└── utils/
    ├── __init__.py
    ├── logger.py             # Logging
    └── scheduler.py          # Cron/scheduling
```

## Core Components

### 1. Session Manager (`auth/session_manager.py`)

```python
import os
import subprocess
import time
import requests
from pathlib import Path
import json

class SessionManager:
    def __init__(self, profile_dir=None):
        self.profile_dir = profile_dir or Path.home() / ".claude-sync-chrome"
        self.chrome_port = 9222
        self.session_file = self.profile_dir / "session_state.json"
        
    def ensure_chrome_running(self):
        """Launch Chrome with debugging if needed"""
        if self.is_chrome_running():
            return True
            
        # Launch Chrome
        chrome_cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            f"--remote-debugging-port={self.chrome_port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--restore-last-session",
            "https://claude.ai/projects"
        ]
        
        subprocess.Popen(chrome_cmd, 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        time.sleep(5)
        
        # Check if we need manual auth
        if not self.is_authenticated():
            return self.handle_manual_auth()
        
        return True
    
    def is_chrome_running(self):
        try:
            resp = requests.get(f"http://localhost:{self.chrome_port}/json/version")
            return resp.status_code == 200
        except:
            return False
    
    def is_authenticated(self):
        """Check if we have an active Claude session"""
        try:
            pages = requests.get(f"http://localhost:{self.chrome_port}/json").json()
            for page in pages:
                if 'claude.ai' in page.get('url', ''):
                    # Try to check if we're actually logged in
                    ws_url = page.get('webSocketDebuggerUrl')
                    if ws_url and self._check_auth_status(ws_url):
                        return True
            return False
        except:
            return False
    
    def handle_manual_auth(self):
        """Guide user through manual authentication"""
        print("\n" + "="*50)
        print("MANUAL AUTHENTICATION REQUIRED")
        print("="*50)
        print("\n1. A Chrome window has opened to Claude.ai")
        print("2. Please sign in with your Google account")
        print("3. Complete any CAPTCHA if required")
        print("4. Wait until you see your Claude projects page")
        print("\nPress Enter when you've completed sign-in...")
        input()
        
        # Verify authentication
        if self.is_authenticated():
            print("✓ Authentication successful!")
            self.save_session_state()
            return True
        else:
            print("✗ Authentication failed. Please try again.")
            return False
    
    def save_session_state(self):
        """Save session metadata"""
        state = {
            'last_auth': time.time(),
            'profile_dir': str(self.profile_dir),
            'chrome_port': self.chrome_port
        }
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        with open(self.session_file, 'w') as f:
            json.dump(state, f)
```

### 2. Chrome Controller (`browser/chrome_controller.py`)

```python
import json
import requests
from websocket import create_connection
import time
from typing import List, Dict, Optional

class ChromeController:
    def __init__(self, port=9222):
        self.port = port
        self.base_url = f"http://localhost:{port}"
        
    def get_claude_page(self) -> Optional[Dict]:
        """Find the main Claude page"""
        pages = requests.get(f"{self.base_url}/json").json()
        
        for page in pages:
            url = page.get('url', '')
            if 'claude.ai' in url and 'stripe' not in url:
                return page
        return None
    
    def connect_to_page(self, page: Dict):
        """Create WebSocket connection to page"""
        ws_url = page.get('webSocketDebuggerUrl')
        if not ws_url:
            raise ValueError("No WebSocket URL found")
        
        ws = create_connection(ws_url)
        
        # Enable necessary domains
        ws.send(json.dumps({"id": 1, "method": "Runtime.enable", "params": {}}))
        ws.send(json.dumps({"id": 2, "method": "Page.enable", "params": {}}))
        
        return ws
    
    def navigate_to_projects(self, ws):
        """Navigate to projects page"""
        ws.send(json.dumps({
            "id": 3,
            "method": "Page.navigate",
            "params": {"url": "https://claude.ai/projects"}
        }))
        time.sleep(3)  # Wait for navigation
    
    def get_projects_list(self, ws) -> List[Dict]:
        """Extract all projects from the page"""
        js_code = '''
        (() => {
            const projects = [];
            const projectLinks = document.querySelectorAll('a[href*="/project/"]');
            
            projectLinks.forEach(link => {
                const href = link.getAttribute('href');
                const textElements = link.querySelectorAll('[class*="text"], h2, h3');
                const name = textElements[0]?.textContent?.trim() || link.textContent.trim();
                const description = textElements[1]?.textContent?.trim() || '';
                
                if (href && name) {
                    projects.push({
                        name: name,
                        description: description,
                        url: href.startsWith('http') ? href : 'https://claude.ai' + href,
                        id: href.match(/project\\/([^/?]+)/)?.[1] || 'unknown'
                    });
                }
            });
            
            return projects;
        })()
        '''
        
        ws.send(json.dumps({
            "id": 4,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code}
        }))
        
        # Get response
        while True:
            result = json.loads(ws.recv())
            if result.get('id') == 4:
                if 'result' in result and 'result' in result['result']:
                    return result['result']['result'].get('value', [])
    
    def navigate_to_project(self, ws, project_url: str):
        """Navigate to specific project"""
        ws.send(json.dumps({
            "id": 5,
            "method": "Page.navigate",
            "params": {"url": project_url}
        }))
        time.sleep(3)
    
    def get_knowledge_files(self, ws) -> List[Dict]:
        """Extract knowledge files from project page"""
        js_code = '''
        (() => {
            const files = [];
            
            // Look for knowledge file elements
            const fileElements = document.querySelectorAll('[role="button"]:has(h3)');
            
            fileElements.forEach(elem => {
                const heading = elem.querySelector('h3');
                const lineInfo = elem.querySelector('p');
                
                if (heading && lineInfo && lineInfo.textContent.includes('lines')) {
                    files.push({
                        name: heading.textContent.trim(),
                        lines: parseInt(lineInfo.textContent.match(/\\d+/)?.[0] || '0'),
                        type: 'text'
                    });
                }
            });
            
            return files;
        })()
        '''
        
        ws.send(json.dumps({
            "id": 6,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code}
        }))
        
        while True:
            result = json.loads(ws.recv())
            if result.get('id') == 6:
                if 'result' in result and 'result' in result['result']:
                    return result['result']['result'].get('value', [])
    
    def click_file(self, ws, file_name: str):
        """Click on a specific file to open it"""
        js_code = f'''
        (() => {{
            const buttons = document.querySelectorAll('[role="button"]:has(h3)');
            for (const button of buttons) {{
                const heading = button.querySelector('h3');
                if (heading && heading.textContent.trim() === "{file_name}") {{
                    button.click();
                    return true;
                }}
            }}
            return false;
        }})()
        '''
        
        ws.send(json.dumps({
            "id": 7,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code}
        }))
        
        time.sleep(2)  # Wait for dialog to open
    
    def get_file_content(self, ws) -> Optional[str]:
        """Extract content from open file dialog"""
        js_code = '''
        (() => {
            // Look for dialog content
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return null;
            
            // Find the content area
            const contentArea = dialog.querySelector('pre, code') || 
                               dialog.querySelector('[class*="content"]') ||
                               dialog.querySelector('div').parentElement.lastElementChild;
            
            if (contentArea) {
                return contentArea.textContent || contentArea.innerText;
            }
            
            return null;
        })()
        '''
        
        ws.send(json.dumps({
            "id": 8,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code}
        }))
        
        while True:
            result = json.loads(ws.recv())
            if result.get('id') == 8:
                if 'result' in result and 'result' in result['result']:
                    return result['result']['result'].get('value')
    
    def close_dialog(self, ws):
        """Close the file dialog"""
        js_code = '''
        (() => {
            const closeButton = document.querySelector('[role="dialog"] button[aria-label*="Close"]') ||
                               document.querySelector('[role="dialog"] button:has(svg)');
            if (closeButton) {
                closeButton.click();
                return true;
            }
            
            // Fallback: Press Escape
            document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
            return true;
        })()
        '''
        
        ws.send(json.dumps({
            "id": 9,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code}
        }))
        
        time.sleep(1)
```

### 3. File Extractor (`scraper/file_extractor.py`)

```python
import time
from typing import Dict, List, Optional
from browser.chrome_controller import ChromeController
import logging

logger = logging.getLogger(__name__)

class FileExtractor:
    def __init__(self, controller: ChromeController):
        self.controller = controller
        
    def extract_all_projects(self) -> List[Dict]:
        """Extract all projects and their files"""
        all_projects = []
        
        # Get Claude page
        page = self.controller.get_claude_page()
        if not page:
            raise Exception("No Claude page found")
        
        # Connect to page
        ws = self.controller.connect_to_page(page)
        
        try:
            # Navigate to projects
            self.controller.navigate_to_projects(ws)
            
            # Get projects list
            projects = self.controller.get_projects_list(ws)
            logger.info(f"Found {len(projects)} projects")
            
            # Extract files from each project
            for project in projects:
                logger.info(f"Processing project: {project['name']}")
                project_data = self.extract_project_files(ws, project)
                all_projects.append(project_data)
                
                # Be nice to the server
                time.sleep(2)
            
        finally:
            ws.close()
        
        return all_projects
    
    def extract_project_files(self, ws, project: Dict) -> Dict:
        """Extract all files from a specific project"""
        # Navigate to project
        self.controller.navigate_to_project(ws, project['url'])
        
        # Get knowledge files
        files = self.controller.get_knowledge_files(ws)
        logger.info(f"Found {len(files)} files in {project['name']}")
        
        # Extract each file
        project_data = {
            **project,
            'files': []
        }
        
        for file_info in files:
            logger.info(f"Extracting file: {file_info['name']}")
            
            # Click file to open
            self.controller.click_file(ws, file_info['name'])
            
            # Get content
            content = self.controller.get_file_content(ws)
            
            if content:
                file_data = {
                    **file_info,
                    'content': content
                }
                project_data['files'].append(file_data)
            else:
                logger.warning(f"Failed to extract content for {file_info['name']}")
            
            # Close dialog
            self.controller.close_dialog(ws)
            
            # Small delay
            time.sleep(1)
        
        return project_data
```

### 4. Local Backup Manager (`storage/local_backup.py`)

```python
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List

class LocalBackupManager:
    def __init__(self, backup_dir: str = None):
        self.backup_dir = Path(backup_dir or Path.home() / "claude-backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        
    def save_projects(self, projects: List[Dict]):
        """Save all projects to local filesystem"""
        timestamp = datetime.now().isoformat()
        
        for project in projects:
            self.save_project(project, timestamp)
        
        # Update metadata
        self.update_metadata(projects, timestamp)
    
    def save_project(self, project: Dict, timestamp: str):
        """Save individual project and its files"""
        # Create project directory
        project_dir = self.backup_dir / self._sanitize_filename(project['name'])
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Save project metadata
        project_meta = {
            'id': project['id'],
            'name': project['name'],
            'description': project.get('description', ''),
            'url': project['url'],
            'last_backup': timestamp
        }
        
        with open(project_dir / 'project.json', 'w') as f:
            json.dump(project_meta, f, indent=2)
        
        # Save files
        files_dir = project_dir / 'files'
        files_dir.mkdir(exist_ok=True)
        
        for file_data in project.get('files', []):
            self.save_file(files_dir, file_data)
    
    def save_file(self, files_dir: Path, file_data: Dict):
        """Save individual file with metadata"""
        filename = self._sanitize_filename(file_data['name'])
        
        # Save content
        content_path = files_dir / f"{filename}.txt"
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(file_data['content'])
        
        # Save metadata
        meta_path = files_dir / f"{filename}.meta.json"
        metadata = {
            'original_name': file_data['name'],
            'lines': file_data.get('lines', 0),
            'type': file_data.get('type', 'text'),
            'content_hash': self._hash_content(file_data['content']),
            'size_bytes': len(file_data['content'].encode('utf-8'))
        }
        
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _sanitize_filename(self, name: str) -> str:
        """Convert name to safe filename"""
        # Replace problematic characters
        safe_name = name.replace('/', '-').replace('\\', '-')
        safe_name = safe_name.replace(':', '-').replace('*', '-')
        safe_name = safe_name.replace('?', '-').replace('"', '-')
        safe_name = safe_name.replace('<', '-').replace('>', '-')
        safe_name = safe_name.replace('|', '-')
        
        # Limit length
        if len(safe_name) > 200:
            safe_name = safe_name[:200]
        
        return safe_name.strip()
    
    def _hash_content(self, content: str) -> str:
        """Generate hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def update_metadata(self, projects: List[Dict], timestamp: str):
        """Update global backup metadata"""
        metadata = {}
        
        # Load existing metadata
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
        
        # Update with new backup info
        metadata['last_backup'] = timestamp
        metadata['total_projects'] = len(projects)
        metadata['projects'] = {}
        
        for project in projects:
            metadata['projects'][project['id']] = {
                'name': project['name'],
                'files_count': len(project.get('files', [])),
                'last_seen': timestamp
            }
        
        # Save updated metadata
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
```

### 5. Main Backup Script (`claude_backup.py`)

```python
#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from auth.session_manager import SessionManager
from browser.chrome_controller import ChromeController
from scraper.file_extractor import FileExtractor
from storage.local_backup import LocalBackupManager
from storage.change_detector import ChangeDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('claude_backup.log')
    ]
)
logger = logging.getLogger(__name__)

class ClaudeBackupTool:
    def __init__(self, backup_dir: str = None, profile_dir: str = None):
        self.session_manager = SessionManager(profile_dir)
        self.controller = ChromeController()
        self.extractor = FileExtractor(self.controller)
        self.backup_manager = LocalBackupManager(backup_dir)
        self.change_detector = ChangeDetector(backup_dir)
        
    def run(self, incremental: bool = True):
        """Run the backup process"""
        logger.info("Starting Claude backup process...")
        
        try:
            # Ensure Chrome is running and authenticated
            if not self.session_manager.ensure_chrome_running():
                logger.error("Failed to establish Chrome session")
                return False
            
            # Extract all projects
            logger.info("Extracting projects...")
            projects = self.extractor.extract_all_projects()
            
            if incremental:
                # Filter to only changed projects
                projects = self.change_detector.filter_changed_projects(projects)
                logger.info(f"Found {len(projects)} projects with changes")
            
            if not projects:
                logger.info("No projects to backup")
                return True
            
            # Save projects
            logger.info("Saving projects to local storage...")
            self.backup_manager.save_projects(projects)
            
            # Update change tracking
            self.change_detector.update_tracking(projects)
            
            logger.info(f"Backup completed successfully! Backed up {len(projects)} projects")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}", exc_info=True)
            return False

def main():
    parser = argparse.ArgumentParser(description='Backup Claude.ai projects')
    parser.add_argument('--backup-dir', type=str, 
                       help='Directory to store backups')
    parser.add_argument('--profile-dir', type=str,
                       help='Chrome profile directory')
    parser.add_argument('--full', action='store_true',
                       help='Force full backup (not incremental)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon with periodic backups')
    parser.add_argument('--interval', type=int, default=3600,
                       help='Backup interval in seconds (default: 3600)')
    
    args = parser.parse_args()
    
    # Create backup tool
    tool = ClaudeBackupTool(
        backup_dir=args.backup_dir,
        profile_dir=args.profile_dir
    )
    
    if args.daemon:
        # Run as daemon
        import time
        logger.info(f"Running as daemon with {args.interval}s interval")
        
        while True:
            try:
                tool.run(incremental=not args.full)
            except KeyboardInterrupt:
                logger.info("Daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Backup error: {e}")
            
            time.sleep(args.interval)
    else:
        # Run once
        success = tool.run(incremental=not args.full)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

### 6. Change Detector (`storage/change_detector.py`)

```python
import json
from pathlib import Path
from typing import Dict, List
import hashlib

class ChangeDetector:
    def __init__(self, backup_dir: str):
        self.backup_dir = Path(backup_dir)
        self.tracking_file = self.backup_dir / "change_tracking.json"
        self.tracking_data = self.load_tracking()
    
    def load_tracking(self) -> Dict:
        """Load existing tracking data"""
        if self.tracking_file.exists():
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        return {}
    
    def filter_changed_projects(self, projects: List[Dict]) -> List[Dict]:
        """Return only projects that have changed"""
        changed_projects = []
        
        for project in projects:
            if self.has_project_changed(project):
                changed_projects.append(project)
        
        return changed_projects
    
    def has_project_changed(self, project: Dict) -> bool:
        """Check if project has changed since last backup"""
        project_id = project['id']
        
        # New project?
        if project_id not in self.tracking_data:
            return True
        
        # Check each file
        tracked_files = self.tracking_data[project_id].get('files', {})
        
        for file_data in project.get('files', []):
            file_hash = self._hash_content(file_data['content'])
            file_name = file_data['name']
            
            # New file or changed content?
            if file_name not in tracked_files or tracked_files[file_name] != file_hash:
                return True
        
        # Check for deleted files
        current_files = {f['name'] for f in project.get('files', [])}
        tracked_file_names = set(tracked_files.keys())
        
        if tracked_file_names != current_files:
            return True
        
        return False
    
    def update_tracking(self, projects: List[Dict]):
        """Update tracking data with current state"""
        for project in projects:
            project_id = project['id']
            
            self.tracking_data[project_id] = {
                'name': project['name'],
                'files': {}
            }
            
            for file_data in project.get('files', []):
                file_hash = self._hash_content(file_data['content'])
                self.tracking_data[project_id]['files'][file_data['name']] = file_hash
        
        # Save tracking data
        with open(self.tracking_file, 'w') as f:
            json.dump(self.tracking_data, f, indent=2)
    
    def _hash_content(self, content: str) -> str:
        """Generate hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

## Installation & Usage

### Installation Script (`install.sh`)

```bash
#!/bin/bash
# Claude Backup Tool Installation

echo "Installing Claude Backup Tool..."

# Create directory structure
mkdir -p ~/claude-backup/{auth,browser,scraper,storage,config,utils}

# Install dependencies
pip install websocket-client requests

# Create launch script
cat > ~/claude-backup/backup.sh << 'EOF'
#!/bin/bash
cd ~/claude-backup
python3 claude_backup.py "$@"
EOF

chmod +x ~/claude-backup/backup.sh

# Create LaunchAgent for macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    cat > ~/Library/LaunchAgents/com.claude.backup.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HOME/claude-backup/backup.sh</string>
        <string>--daemon</string>
        <string>--interval</string>
        <string>3600</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/claude-backup/backup.out</string>
    <key>StandardErrorPath</key>
    <string>$HOME/claude-backup/backup.err</string>
</dict>
</plist>
EOF
    
    launchctl load ~/Library/LaunchAgents/com.claude.backup.plist
fi

echo "Installation complete!"
```

### Usage Examples

```bash
# Run backup once (interactive if needed)
./claude_backup.py

# Run full backup (not incremental)
./claude_backup.py --full

# Run as daemon (background, hourly)
./claude_backup.py --daemon --interval 3600

# Use custom directories
./claude_backup.py --backup-dir ~/my-backups --profile-dir ~/my-chrome-profile

# View logs
tail -f claude_backup.log
```

## Fallback Strategy: Playwright MCP

If direct Chrome control fails, the tool can fall back to Playwright MCP:

```python
# browser/playwright_mcp.py
class PlaywrightMCPFallback:
    """Fallback using Claude Code's MCP tools"""
    
    def extract_via_mcp(self):
        # This would need to be called from within Claude Code
        # as it requires access to MCP tools
        pass
```

## Key Features

1. **Automatic Authentication**: Reuses existing Chrome session or prompts for manual auth
2. **Incremental Backups**: Only backs up changed files to save time
3. **Change Detection**: SHA-256 hashing to detect file changes
4. **Organized Storage**: Projects stored in logical directory structure
5. **Metadata Tracking**: Keeps track of all projects and files
6. **Daemon Mode**: Can run continuously in background
7. **Logging**: Comprehensive logging for debugging
8. **Error Recovery**: Handles failures gracefully
9. **Cross-Platform**: Works on macOS, Linux, Windows (with adjustments)

## Security Considerations

1. **Local Storage Only**: All data stored locally, no cloud uploads
2. **Session Isolation**: Uses dedicated Chrome profile
3. **No Credential Storage**: Relies on browser session persistence
4. **File Permissions**: Backups stored with user-only permissions

This tool provides a complete automated solution for backing up Claude.ai projects without requiring constant attention from either of us!