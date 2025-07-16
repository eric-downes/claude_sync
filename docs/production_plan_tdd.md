# Claude Sync - TDD Production Implementation Plan

## Technology Stack

- **Chrome Control**: `pychrome` (async, typed)
- **HTML Parsing**: `beautifulsoup4` 
- **Testing**: `pytest` + `pytest-asyncio`
- **Data Models**: `pydantic` (already in use)
- **Configuration**: `pydantic-settings`

## Architecture Overview

```
claude_sync/
├── src/
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── chrome_manager.py      # Manages Chrome lifecycle (headless, persistent)
│   │   └── connection.py          # pychrome connection wrapper
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py               # Base extractor with BeautifulSoup
│   │   ├── projects.py           # Project list extraction
│   │   └── knowledge.py          # Knowledge file extraction
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py            # Pydantic models
│   │   └── knowledge.py
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── manager.py            # Main sync orchestrator
│   │   └── scheduler.py          # Sporadic sync logic
│   ├── storage/
│   │   ├── __init__.py
│   │   └── local.py              # Save to disk
│   └── config.py                 # Settings management
├── tests/
│   ├── unit/
│   │   ├── test_extractors.py
│   │   ├── test_models.py
│   │   └── test_storage.py
│   ├── integration/
│   │   ├── test_browser.py
│   │   └── test_sync.py
│   └── fixtures/
│       ├── html_samples.py       # Real HTML for testing
│       └── mock_chrome.py
├── scripts/
│   └── sync_claude.py            # CLI entry point
└── pyproject.toml               # Modern Python packaging
```

## TDD Implementation Steps

### Step 1: Core Models (30 min)
```python
# tests/unit/test_models.py
import pytest
from datetime import datetime
from src.models import Project, KnowledgeFile

def test_project_model():
    project = Project(
        id="test-123",
        name="Test Project",
        description="Test Description",
        url="https://claude.ai/project/test-123"
    )
    assert project.id == "test-123"
    assert project.name == "Test Project"

def test_knowledge_file_model():
    file = KnowledgeFile(
        name="test.py",
        content="print('hello')",
        file_type="python",
        lines=1
    )
    assert file.name == "test.py"
    assert file.lines == 1
```

### Step 2: HTML Extraction with BeautifulSoup (1 hour)
```python
# tests/unit/test_extractors.py
import pytest
from bs4 import BeautifulSoup
from src.extractors import ProjectExtractor, KnowledgeExtractor
from tests.fixtures.html_samples import PROJECTS_PAGE_HTML, PROJECT_PAGE_HTML

def test_extract_projects_from_html():
    extractor = ProjectExtractor()
    soup = BeautifulSoup(PROJECTS_PAGE_HTML, 'html.parser')
    projects = extractor.extract_from_soup(soup)
    
    assert len(projects) > 0
    assert projects[0].name == "DNI"
    assert projects[0].description == "EU-only MLETR"

def test_extract_knowledge_files():
    extractor = KnowledgeExtractor()
    soup = BeautifulSoup(PROJECT_PAGE_HTML, 'html.parser')
    files = extractor.extract_from_soup(soup)
    
    assert len(files) == 7
    assert any(f.name == "Invoice valuation" for f in files)
```

### Step 3: Chrome Connection with pychrome (1 hour)
```python
# tests/integration/test_browser.py
import pytest
import asyncio
from src.browser import ChromeManager, ChromeConnection

@pytest.mark.asyncio
async def test_chrome_manager_lifecycle():
    manager = ChromeManager(headless=True)
    
    # Start Chrome
    await manager.start()
    assert manager.is_running()
    assert manager.get_memory_usage() < 100  # MB
    
    # Connect
    async with ChromeConnection(manager.debug_port) as conn:
        # Test navigation
        page = await conn.get_or_create_page()
        await page.navigate("https://example.com")
        
        # Get HTML
        html = await page.get_html()
        assert "<html" in html
    
    # Stop Chrome
    await manager.stop()
    assert not manager.is_running()

@pytest.mark.asyncio
async def test_persistent_chrome():
    manager = ChromeManager(persistent=True, profile_dir="~/.claude-sync-test")
    
    # Start and stop
    await manager.start()
    pid1 = manager.get_pid()
    
    # Don't stop - just disconnect
    manager = ChromeManager(persistent=True, profile_dir="~/.claude-sync-test")
    await manager.connect_existing()
    pid2 = manager.get_pid()
    
    assert pid1 == pid2  # Same Chrome instance
```

### Step 4: Full Sync Flow (2 hours)
```python
# tests/integration/test_sync.py
import pytest
from src.sync import ClaudeSyncManager
from src.storage import LocalStorage

@pytest.mark.asyncio
async def test_full_sync_flow(mock_chrome_with_claude):
    storage = LocalStorage("./test_output")
    manager = ClaudeSyncManager(
        chrome_manager=mock_chrome_with_claude,
        storage=storage
    )
    
    # Check auth
    assert await manager.check_auth()
    
    # Sync projects
    projects = await manager.sync_projects()
    assert len(projects) > 0
    
    # Sync knowledge files for each project
    for project in projects:
        files = await manager.sync_project_knowledge(project)
        assert len(files) >= 0
    
    # Verify storage
    saved_projects = storage.get_all_projects()
    assert len(saved_projects) == len(projects)
```

### Step 5: Sporadic Sync Logic (1 hour)
```python
# tests/unit/test_scheduler.py
import pytest
from unittest.mock import Mock, patch
from src.sync import SporadicScheduler

def test_should_sync_conditions():
    scheduler = SporadicScheduler()
    
    # Test internet check
    with patch('subprocess.check_output') as mock_ping:
        mock_ping.side_effect = Exception()  # No internet
        assert not scheduler.should_sync()
    
    # Test battery check
    with patch('subprocess.check_output') as mock_cmd:
        mock_cmd.return_value = b"Battery Power: 25%"
        assert not scheduler.should_sync()
        
        mock_cmd.return_value = b"AC Power"
        assert scheduler.should_sync()
    
    # Test recent sync
    scheduler.mark_sync_complete()
    assert not scheduler.should_sync()  # Too soon
```

## Key Implementation Details

### 1. Chrome Manager (pychrome)
```python
# src/browser/chrome_manager.py
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
import pychrome

class ChromeManager:
    def __init__(self, 
                 headless: bool = True,
                 persistent: bool = True,
                 profile_dir: Optional[str] = None):
        self.headless = headless
        self.persistent = persistent
        self.profile_dir = Path(profile_dir or "~/.claude-sync-profile").expanduser()
        self.port = 9222
        self._process: Optional[subprocess.Popen] = None
        self._browser: Optional[pychrome.Browser] = None
    
    async def start(self) -> None:
        """Start Chrome with optimized settings."""
        if self.is_running():
            return
        
        cmd = self._build_chrome_command()
        self._process = subprocess.Popen(cmd, 
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
        
        # Wait for Chrome to be ready
        await self._wait_for_chrome()
        
    def _build_chrome_command(self) -> List[str]:
        cmd = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.profile_dir}",
        ]
        
        if self.headless:
            cmd.extend([
                "--headless",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                # ... memory optimization flags
            ])
        
        return cmd
```

### 2. Extractor with BeautifulSoup
```python
# src/extractors/projects.py
from typing import List
from bs4 import BeautifulSoup, Tag
from src.models import Project

class ProjectExtractor:
    def extract_from_html(self, html: str) -> List[Project]:
        """Extract projects from HTML string."""
        soup = BeautifulSoup(html, 'html.parser')
        return self.extract_from_soup(soup)
    
    def extract_from_soup(self, soup: BeautifulSoup) -> List[Project]:
        """Extract projects from BeautifulSoup object."""
        projects = []
        
        # Find all project links
        for link in soup.select('a[href*="/project/"]'):
            project = self._parse_project_card(link)
            if project:
                projects.append(project)
        
        return projects
    
    def _parse_project_card(self, link: Tag) -> Optional[Project]:
        """Parse a single project card."""
        href = link.get('href', '')
        if not href:
            return None
        
        # Extract ID from URL
        project_id = href.split('/project/')[-1] if '/project/' in href else None
        
        # Find nested structure
        container = link.find('div')
        if not container:
            return None
        
        divs = container.find_all('div', recursive=False)
        
        # Parse title and description
        name = divs[0].get_text(strip=True) if len(divs) > 0 else None
        description = None
        
        if len(divs) > 1:
            desc_text = divs[1].get_text(strip=True)
            if 'Updated' not in desc_text:
                description = desc_text
        
        if name and project_id:
            return Project(
                id=project_id,
                name=name,
                description=description,
                url=f"https://claude.ai{href}" if href.startswith('/') else href
            )
        
        return None
```

### 3. Async Sync Manager
```python
# src/sync/manager.py
import asyncio
from typing import List
from src.browser import ChromeManager, ChromeConnection
from src.extractors import ProjectExtractor, KnowledgeExtractor
from src.models import Project, KnowledgeFile

class ClaudeSyncManager:
    def __init__(self, chrome_manager: ChromeManager, storage):
        self.chrome = chrome_manager
        self.storage = storage
        self.project_extractor = ProjectExtractor()
        self.knowledge_extractor = KnowledgeExtractor()
    
    async def check_auth(self) -> bool:
        """Check if we're authenticated to Claude."""
        async with ChromeConnection(self.chrome.port) as conn:
            page = await conn.get_or_create_page()
            await page.navigate("https://claude.ai/projects")
            
            # Check URL after navigation
            current_url = await page.evaluate("window.location.href")
            return "login" not in current_url
    
    async def sync_projects(self) -> List[Project]:
        """Sync all projects."""
        async with ChromeConnection(self.chrome.port) as conn:
            page = await conn.get_or_create_page()
            await page.navigate("https://claude.ai/projects")
            await page.wait_for_selector('a[href*="/project/"]')
            
            # Get HTML and extract
            html = await page.get_html()
            projects = self.project_extractor.extract_from_html(html)
            
            # Save to storage
            for project in projects:
                self.storage.save_project(project)
            
            return projects
```

## Migration Path

1. **Week 1**: Implement core models and extractors with tests
2. **Week 2**: Chrome management and connection layer
3. **Week 3**: Full sync flow and storage
4. **Week 4**: Polish, error handling, and sporadic sync

## Benefits of This Approach

1. **Type Safety**: Full typing with pychrome + pydantic
2. **Testability**: Everything is unit testable
3. **Reliability**: Async/await prevents timing issues
4. **Maintainability**: Clean separation of concerns
5. **Performance**: Efficient async operations
6. **Memory**: Controlled Chrome lifecycle

Ready to start implementing this step by step?