"""Tests for data models."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from claude_sync.models import Project, KnowledgeFile, SyncState


class TestProjectModel:
    """Test Project model."""
    
    def test_project_minimal(self):
        """Test creating project with minimal data."""
        project = Project(
            id="test-123",
            name="Test Project",
            url="https://claude.ai/project/test-123"
        )
        assert project.id == "test-123"
        assert project.name == "Test Project"
        assert project.url == "https://claude.ai/project/test-123"
        assert project.description is None
        assert project.updated_at is None
    
    def test_project_complete(self):
        """Test creating project with all fields."""
        now = datetime.now()
        project = Project(
            id="test-123",
            name="Test Project",
            url="https://claude.ai/project/test-123",
            description="A test project",
            updated_at=now
        )
        assert project.description == "A test project"
        assert project.updated_at == now
    
    def test_project_validation(self):
        """Test project validation."""
        # Missing required fields
        with pytest.raises(ValidationError):
            Project(id="test-123", name="Test")  # Missing URL
        
        with pytest.raises(ValidationError):
            Project(id="", name="Test", url="https://test.com")  # Empty ID
    
    def test_project_dict_export(self):
        """Test exporting project to dict."""
        project = Project(
            id="test-123",
            name="Test Project",
            url="https://claude.ai/project/test-123",
            description="Test"
        )
        data = project.model_dump(exclude_none=True)
        assert data == {
            "id": "test-123",
            "name": "Test Project",
            "url": "https://claude.ai/project/test-123",
            "description": "Test"
        }


class TestKnowledgeFileModel:
    """Test KnowledgeFile model."""
    
    def test_knowledge_file_text(self):
        """Test creating text knowledge file."""
        file = KnowledgeFile(
            name="test.py",
            file_type="text",
            lines=42
        )
        assert file.name == "test.py"
        assert file.file_type == "text"
        assert file.lines == 42
        assert file.content is None
        assert file.size_bytes is None
    
    def test_knowledge_file_pdf(self):
        """Test creating PDF knowledge file."""
        file = KnowledgeFile(
            name="document.pdf",
            file_type="pdf"
        )
        assert file.name == "document.pdf"
        assert file.file_type == "pdf"
        assert file.lines is None
    
    def test_knowledge_file_with_content(self):
        """Test knowledge file with content."""
        content = "def hello():\n    print('world')"
        file = KnowledgeFile(
            name="hello.py",
            file_type="text",
            lines=2,
            content=content,
            size_bytes=len(content.encode())
        )
        assert file.content == content
        assert file.size_bytes == len(content.encode())
    
    def test_knowledge_file_validation(self):
        """Test knowledge file validation."""
        # Empty name
        with pytest.raises(ValidationError):
            KnowledgeFile(name="", file_type="text")
        
        # Invalid file type
        with pytest.raises(ValidationError):
            KnowledgeFile(name="test.txt", file_type="invalid")
    
    def test_knowledge_file_hash(self):
        """Test content hash calculation."""
        file = KnowledgeFile(
            name="test.txt",
            file_type="text",
            content="Hello, world!"
        )
        hash1 = file.calculate_content_hash()
        assert hash1 is not None
        assert len(hash1) == 64  # SHA-256 hex string
        
        # Same content = same hash
        file2 = KnowledgeFile(
            name="different.txt",
            file_type="text",
            content="Hello, world!"
        )
        assert file2.calculate_content_hash() == hash1
        
        # Different content = different hash
        file3 = KnowledgeFile(
            name="test.txt",
            file_type="text",
            content="Goodbye, world!"
        )
        assert file3.calculate_content_hash() != hash1


class TestSyncStateModel:
    """Test SyncState model."""
    
    def test_sync_state_creation(self):
        """Test creating sync state."""
        now = datetime.now()
        state = SyncState(
            last_sync=now,
            project_count=5,
            status="success"
        )
        assert state.last_sync == now
        assert state.project_count == 5
        assert state.status == "success"
        assert state.error is None
    
    def test_sync_state_with_error(self):
        """Test sync state with error."""
        state = SyncState(
            last_sync=datetime.now(),
            project_count=0,
            status="error",
            error="Authentication failed"
        )
        assert state.status == "error"
        assert state.error == "Authentication failed"
    
    def test_sync_state_validation(self):
        """Test sync state validation."""
        # Invalid status
        with pytest.raises(ValidationError):
            SyncState(
                last_sync=datetime.now(),
                project_count=0,
                status="invalid"
            )
    
    def test_hours_since_sync(self):
        """Test calculating hours since last sync."""
        from datetime import timedelta
        
        # Recent sync
        state = SyncState(
            last_sync=datetime.now() - timedelta(hours=2),
            project_count=5,
            status="success"
        )
        assert 1.9 < state.hours_since_sync < 2.1
        
        # Old sync
        state = SyncState(
            last_sync=datetime.now() - timedelta(days=1),
            project_count=5,
            status="success"
        )
        assert 23.9 < state.hours_since_sync < 24.1