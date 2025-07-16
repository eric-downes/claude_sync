"""Tests for sync storage module."""
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from claude_sync.sync.storage import LocalStorage
from claude_sync.models import Project, KnowledgeFile


class TestLocalStorage:
    """Test LocalStorage class."""
    
    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage for testing."""
        return LocalStorage(tmp_path)
    
    @pytest.fixture
    def sample_project(self):
        """Create sample project."""
        return Project(
            id="123",
            name="Test Project",
            description="A test project",
            url="https://claude.ai/project/123"
        )
    
    @pytest.fixture
    def sample_file(self):
        """Create sample knowledge file."""
        return KnowledgeFile(
            name="test.txt",
            file_type="text",
            lines=100
        )
    
    def test_init_creates_directories(self, tmp_path):
        """Test storage initialization creates required directories."""
        storage = LocalStorage(tmp_path)
        
        assert storage.base_path.exists()
        assert storage.projects_dir.exists()
        assert storage.metadata_dir.exists()
        assert (tmp_path / "projects").exists()
        assert (tmp_path / ".metadata").exists()
    
    def test_get_project_path(self, temp_storage, sample_project):
        """Test getting project path."""
        path = temp_storage.get_project_path(sample_project)
        
        assert path == temp_storage.projects_dir / "Test Project"
        assert path.parent == temp_storage.projects_dir
    
    def test_save_project_metadata(self, temp_storage, sample_project):
        """Test saving project metadata."""
        temp_storage.save_project_metadata(sample_project)
        
        project_path = temp_storage.get_project_path(sample_project)
        metadata_file = project_path / "project.json"
        
        assert project_path.exists()
        assert metadata_file.exists()
        
        with open(metadata_file) as f:
            metadata = json.load(f)
        
        assert metadata["name"] == "Test Project"
        assert metadata["description"] == "A test project"
        assert metadata["url"] == "https://claude.ai/project/123"
        assert metadata["project_id"] == "123"
        assert "last_synced" in metadata
    
    def test_save_knowledge_file(self, temp_storage, sample_project, sample_file):
        """Test saving knowledge file."""
        content = "This is test content\nWith multiple lines"
        
        # Create project directory first
        temp_storage.save_project_metadata(sample_project)
        
        saved_path = temp_storage.save_knowledge_file(
            sample_project, sample_file, content
        )
        
        assert saved_path.exists()
        assert saved_path.parent.name == "knowledge"
        assert saved_path.name == "test.txt.text"
        
        with open(saved_path) as f:
            assert f.read() == content
    
    def test_save_knowledge_file_handles_duplicates(self, temp_storage, sample_project, sample_file):
        """Test handling duplicate filenames."""
        content1 = "First file"
        content2 = "Second file"
        
        # Create project directory first
        temp_storage.save_project_metadata(sample_project)
        
        # Save first file
        path1 = temp_storage.save_knowledge_file(sample_project, sample_file, content1)
        
        # Save second file with same name
        path2 = temp_storage.save_knowledge_file(sample_project, sample_file, content2)
        
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()
        assert path2.name == "test.txt_1.text"
    
    def test_sanitize_name(self, temp_storage):
        """Test filename sanitization."""
        # Test various problematic characters
        assert temp_storage._sanitize_name("file/name") == "file-name"
        assert temp_storage._sanitize_name("file:name") == "file-name"
        assert temp_storage._sanitize_name("file*name") == "file-name"
        assert temp_storage._sanitize_name("file?name") == "file-name"
        assert temp_storage._sanitize_name('file"name') == "filename"
        assert temp_storage._sanitize_name("file<>name") == "file--name"
        assert temp_storage._sanitize_name("file|name") == "file-name"
        assert temp_storage._sanitize_name("file\nname") == "file name"
        assert temp_storage._sanitize_name("   file   name   ") == "file name"
        
        # Test length limiting
        long_name = "a" * 300
        assert len(temp_storage._sanitize_name(long_name)) == 200
        
        # Test empty result fallback
        assert temp_storage._sanitize_name("***") == "---"
    
    def test_get_sync_state_empty(self, temp_storage):
        """Test getting sync state when none exists."""
        state = temp_storage.get_sync_state()
        
        assert state["last_sync"] is None
        assert state["projects_synced"] == []
        assert state["total_files"] == 0
        assert state["version"] == "1.0"
    
    def test_update_sync_state(self, temp_storage):
        """Test updating sync state."""
        new_state = {
            "last_sync": datetime.now().isoformat(),
            "projects_synced": ["Project1", "Project2"],
            "total_files": 10,
            "version": "1.0"
        }
        
        temp_storage.update_sync_state(new_state)
        
        # Read it back
        state = temp_storage.get_sync_state()
        assert state == new_state
    
    def test_get_project_sync_status_not_synced(self, temp_storage, sample_project):
        """Test sync status for unsynced project."""
        status = temp_storage.get_project_sync_status(sample_project)
        
        assert status["synced"] is False
        assert status["last_synced"] is None
        assert status["files_count"] == 0
    
    def test_get_project_sync_status_synced(self, temp_storage, sample_project, sample_file):
        """Test sync status for synced project."""
        # Save project and a file
        temp_storage.save_project_metadata(sample_project)
        temp_storage.save_knowledge_file(sample_project, sample_file, "content")
        
        status = temp_storage.get_project_sync_status(sample_project)
        
        assert status["synced"] is True
        assert status["last_synced"] is not None
        assert status["files_count"] == 1
    
    def test_list_synced_projects(self, temp_storage):
        """Test listing synced projects."""
        # Create multiple projects
        projects = [
            Project(id=str(i), name=f"Project {i}", url=f"https://claude.ai/project/{i}")
            for i in range(3)
        ]
        
        for project in projects:
            temp_storage.save_project_metadata(project)
        
        synced = temp_storage.list_synced_projects()
        
        assert len(synced) == 3
        assert all("local_path" in p for p in synced)
        assert sorted([p["name"] for p in synced]) == ["Project 0", "Project 1", "Project 2"]