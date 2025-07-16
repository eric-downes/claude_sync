"""Local storage management for synced Claude data."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from claude_sync.models import Project, KnowledgeFile

logger = logging.getLogger(__name__)


class LocalStorage:
    """Manages local storage of synced Claude data."""
    
    def __init__(self, base_path: Path):
        """Initialize storage with base path.
        
        Args:
            base_path: Base directory for storing synced data
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Standard directory structure
        self.projects_dir = self.base_path / "projects"
        self.metadata_dir = self.base_path / ".metadata"
        
        # Create directories
        self.projects_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
    
    def get_project_path(self, project: Project) -> Path:
        """Get local path for a project.
        
        Args:
            project: Project object
            
        Returns:
            Path to project directory
        """
        # Create safe directory name from project name
        safe_name = self._sanitize_name(project.name)
        return self.projects_dir / safe_name
    
    def save_project_metadata(self, project: Project) -> None:
        """Save project metadata.
        
        Args:
            project: Project object to save
        """
        project_path = self.get_project_path(project)
        project_path.mkdir(exist_ok=True)
        
        # Save project info
        metadata = {
            "name": project.name,
            "description": project.description,
            "url": project.url,
            "last_synced": datetime.now().isoformat(),
            "project_id": project.url.split("/")[-1]  # Extract ID from URL
        }
        
        metadata_file = project_path / "project.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved metadata for project: {project.name}")
    
    def save_knowledge_file(
        self, 
        project: Project, 
        file: KnowledgeFile, 
        content: str
    ) -> Path:
        """Save a knowledge file.
        
        Args:
            project: Project containing the file
            file: KnowledgeFile metadata
            content: File content
            
        Returns:
            Path to saved file
        """
        project_path = self.get_project_path(project)
        knowledge_dir = project_path / "knowledge"
        knowledge_dir.mkdir(exist_ok=True)
        
        # Create safe filename
        safe_name = self._sanitize_name(file.name)
        if not safe_name.endswith(f".{file.file_type}"):
            safe_name = f"{safe_name}.{file.file_type}"
        
        file_path = knowledge_dir / safe_name
        
        # Handle potential duplicates
        if file_path.exists():
            base_name = file_path.stem
            extension = file_path.suffix
            counter = 1
            while file_path.exists():
                file_path = knowledge_dir / f"{base_name}_{counter}{extension}"
                counter += 1
        
        # Save content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved knowledge file: {file_path}")
        return file_path
    
    def get_sync_state(self) -> Dict[str, Any]:
        """Get current sync state.
        
        Returns:
            Dictionary with sync state information
        """
        state_file = self.metadata_dir / "sync_state.json"
        
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        
        return {
            "last_sync": None,
            "projects_synced": [],
            "total_files": 0,
            "version": "1.0"
        }
    
    def update_sync_state(self, state: Dict[str, Any]) -> None:
        """Update sync state.
        
        Args:
            state: New sync state
        """
        state_file = self.metadata_dir / "sync_state.json"
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def get_project_sync_status(self, project: Project) -> Dict[str, Any]:
        """Get sync status for a specific project.
        
        Args:
            project: Project to check
            
        Returns:
            Sync status information
        """
        project_path = self.get_project_path(project)
        metadata_file = project_path / "project.json"
        
        if not metadata_file.exists():
            return {
                "synced": False,
                "last_synced": None,
                "files_count": 0
            }
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Count knowledge files
        knowledge_dir = project_path / "knowledge"
        files_count = len(list(knowledge_dir.glob("*"))) if knowledge_dir.exists() else 0
        
        return {
            "synced": True,
            "last_synced": metadata.get("last_synced"),
            "files_count": files_count
        }
    
    def list_synced_projects(self) -> List[Dict[str, Any]]:
        """List all synced projects.
        
        Returns:
            List of project metadata
        """
        projects = []
        
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                metadata_file = project_dir / "project.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Add local path info
                    metadata["local_path"] = str(project_dir)
                    projects.append(metadata)
        
        return projects
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for filesystem.
        
        Args:
            name: Original name
            
        Returns:
            Sanitized name safe for filesystem
        """
        # Replace problematic characters
        replacements = {
            '/': '-',
            '\\': '-',
            ':': '-',
            '*': '-',
            '?': '-',
            '"': '',
            '<': '-',
            '>': '-',
            '|': '-',
            '\n': ' ',
            '\r': ' '
        }
        
        safe_name = name
        for old, new in replacements.items():
            safe_name = safe_name.replace(old, new)
        
        # Remove multiple spaces and trim
        safe_name = ' '.join(safe_name.split())
        
        # Limit length
        if len(safe_name) > 200:
            safe_name = safe_name[:200]
        
        return safe_name.strip() or "unnamed"