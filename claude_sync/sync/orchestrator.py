"""Orchestrates the sync process for Claude.ai data."""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from claude_sync.browser import BrowserConfig, ChromeManager, ChromeConnection
from claude_sync.models import Project, KnowledgeFile
from .storage import LocalStorage

logger = logging.getLogger(__name__)


class SyncProgress:
    """Tracks sync progress."""
    
    def __init__(self):
        self.total_projects = 0
        self.completed_projects = 0
        self.total_files = 0
        self.completed_files = 0
        self.current_project: Optional[str] = None
        self.current_file: Optional[str] = None
        self.errors: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_projects": self.total_projects,
            "completed_projects": self.completed_projects,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "current_project": self.current_project,
            "current_file": self.current_file,
            "errors": self.errors,
            "progress_percent": self._calculate_progress()
        }
    
    def _calculate_progress(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.completed_files / self.total_files) * 100


class SyncOrchestrator:
    """Orchestrates the sync process."""
    
    def __init__(
        self, 
        storage_path: Path,
        browser_config: Optional[BrowserConfig] = None,
        progress_callback: Optional[Callable[[SyncProgress], None]] = None
    ):
        """Initialize orchestrator.
        
        Args:
            storage_path: Path for local storage
            browser_config: Browser configuration
            progress_callback: Optional callback for progress updates
        """
        self.storage = LocalStorage(storage_path)
        self.browser_config = browser_config or BrowserConfig()
        self.progress_callback = progress_callback
        self.progress = SyncProgress()
    
    async def sync_all(self, filter_projects: Optional[List[str]] = None) -> Dict[str, Any]:
        """Sync all projects and their knowledge files.
        
        Args:
            filter_projects: Optional list of project names to sync (None = all)
            
        Returns:
            Sync summary
        """
        start_time = datetime.now()
        logger.info("Starting full sync...")
        
        manager = ChromeManager(self.browser_config)
        
        try:
            browser = await manager.get_or_create_browser()
            connection = ChromeConnection(browser)
            
            # Check login
            if not await connection.is_logged_in():
                raise Exception("Not logged in to Claude.ai")
            
            # Get all projects
            logger.info("Fetching project list...")
            await connection.navigate("https://claude.ai/projects")
            await asyncio.sleep(3)
            
            projects = await connection.extract_projects()
            logger.info(f"Found {len(projects)} projects")
            
            # Filter if requested
            if filter_projects:
                projects = [p for p in projects if p.name in filter_projects]
                logger.info(f"Filtered to {len(projects)} projects")
            
            # Update progress
            self.progress.total_projects = len(projects)
            self._update_progress()
            
            # Sync each project
            for project in projects:
                await self._sync_project(connection, project)
            
            # Update sync state
            sync_state = self.storage.get_sync_state()
            sync_state["last_sync"] = datetime.now().isoformat()
            sync_state["projects_synced"] = [p.name for p in projects]
            sync_state["total_files"] = self.progress.completed_files
            self.storage.update_sync_state(sync_state)
            
            # Summary
            duration = (datetime.now() - start_time).total_seconds()
            summary = {
                "success": True,
                "duration_seconds": duration,
                "projects_synced": self.progress.completed_projects,
                "files_synced": self.progress.completed_files,
                "errors": self.progress.errors
            }
            
            logger.info(f"Sync completed in {duration:.1f}s")
            return summary
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "progress": self.progress.to_dict()
            }
        finally:
            await manager.close()
    
    async def sync_project(self, project_name: str) -> Dict[str, Any]:
        """Sync a single project.
        
        Args:
            project_name: Name of project to sync
            
        Returns:
            Sync summary for the project
        """
        return await self.sync_all(filter_projects=[project_name])
    
    async def _sync_project(
        self, 
        connection: ChromeConnection, 
        project: Project
    ) -> None:
        """Sync a single project.
        
        Args:
            connection: Browser connection
            project: Project to sync
        """
        logger.info(f"Syncing project: {project.name}")
        self.progress.current_project = project.name
        self._update_progress()
        
        try:
            # Save project metadata
            self.storage.save_project_metadata(project)
            
            # Navigate to project
            await connection.navigate(project.url, timeout=90000)
            await asyncio.sleep(5)  # Let page fully load
            
            # Extract knowledge files
            files = await connection.extract_knowledge_files()
            logger.info(f"Found {len(files)} knowledge files in {project.name}")
            
            # Update progress
            self.progress.total_files += len(files)
            self._update_progress()
            
            # Download each file
            for file in files:
                await self._sync_knowledge_file(connection, project, file)
            
            # Mark project complete
            self.progress.completed_projects += 1
            self._update_progress()
            
        except Exception as e:
            logger.error(f"Failed to sync project {project.name}: {e}")
            self.progress.errors.append({
                "type": "project_sync",
                "project": project.name,
                "error": str(e)
            })
    
    async def _sync_knowledge_file(
        self,
        connection: ChromeConnection,
        project: Project,
        file: KnowledgeFile
    ) -> None:
        """Sync a single knowledge file.
        
        Args:
            connection: Browser connection
            project: Project containing the file
            file: File to sync
        """
        logger.info(f"Downloading: {file.name}")
        self.progress.current_file = file.name
        self._update_progress()
        
        try:
            # Check if already synced
            project_status = self.storage.get_project_sync_status(project)
            if project_status["synced"]:
                # For now, always re-download
                # TODO: Add checksum/modification time checking
                pass
            
            # Download content
            content = await connection.download_file_content(file.name)
            
            if content is None:
                # Try alternative download method
                logger.warning(f"Standard download failed for {file.name}, trying alternative...")
                content = await self._alternative_download(connection, file)
            
            if content:
                # Save file
                saved_path = self.storage.save_knowledge_file(project, file, content)
                logger.info(f"Saved: {saved_path}")
            else:
                raise Exception("Failed to download file content")
            
            # Update progress
            self.progress.completed_files += 1
            self._update_progress()
            
        except Exception as e:
            logger.error(f"Failed to sync file {file.name}: {e}")
            self.progress.errors.append({
                "type": "file_sync",
                "project": project.name,
                "file": file.name,
                "error": str(e)
            })
    
    async def _alternative_download(
        self,
        connection: ChromeConnection,
        file: KnowledgeFile
    ) -> Optional[str]:
        """Alternative download method using page interaction.
        
        Args:
            connection: Browser connection
            file: File to download
            
        Returns:
            File content or None
        """
        page = await connection.get_or_create_page()
        
        try:
            # Find the file thumbnail
            thumbnails = await page.query_selector_all('div[data-testid="file-thumbnail"]')
            
            for thumb in thumbnails:
                # Check if this is our file
                h3 = await thumb.query_selector('h3')
                if h3:
                    name = await h3.text_content()
                    if name and name.strip() == file.name:
                        # Click to open file
                        button = await thumb.query_selector('button')
                        if button:
                            await button.click()
                            await asyncio.sleep(2)
                            
                            # Look for file content in modal or new view
                            # This would need to be adapted based on Claude's UI
                            # For now, return None
                            logger.warning("Alternative download not fully implemented")
                            return None
            
        except Exception as e:
            logger.error(f"Alternative download failed: {e}")
        
        return None
    
    def _update_progress(self):
        """Update progress and call callback if set."""
        if self.progress_callback:
            self.progress_callback(self.progress)
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get overall sync status.
        
        Returns:
            Status information
        """
        sync_state = self.storage.get_sync_state()
        synced_projects = self.storage.list_synced_projects()
        
        return {
            "last_sync": sync_state.get("last_sync"),
            "total_projects": len(synced_projects),
            "total_files": sync_state.get("total_files", 0),
            "synced_projects": synced_projects
        }