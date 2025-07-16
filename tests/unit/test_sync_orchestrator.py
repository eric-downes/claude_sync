"""Tests for sync orchestrator module."""
import asyncio
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from claude_sync.sync.orchestrator import SyncOrchestrator
from claude_sync.sync.storage import LocalStorage
from claude_sync.browser import ChromeManager, ChromeConnection, BrowserConfig
from claude_sync.models import Project, KnowledgeFile


class TestSyncOrchestrator:
    """Test SyncOrchestrator class."""
    
    @pytest.fixture
    def mock_browser_config(self):
        """Create mock browser config."""
        return BrowserConfig(
            headless=True,
            user_data_dir=Path("/tmp/test-chrome"),
            remote_debugging_port=9222
        )
    
    @pytest.fixture
    def mock_storage(self, tmp_path):
        """Create real storage instance."""
        return LocalStorage(tmp_path)
    
    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Create SyncOrchestrator instance."""
        return SyncOrchestrator(tmp_path)
    
    @pytest.fixture
    def sample_projects(self):
        """Create sample projects."""
        return [
            Project(
                id="1",
                name="Project 1",
                description="First project",
                url="https://claude.ai/project/1"
            ),
            Project(
                id="2",
                name="Project 2",
                description="Second project",
                url="https://claude.ai/project/2"
            ),
        ]
    
    @pytest.fixture
    def sample_files(self):
        """Create sample knowledge files."""
        return [
            KnowledgeFile(
                name="file1.txt",
                file_type="text",
                lines=100
            ),
            KnowledgeFile(
                name="file2.pdf",
                file_type="pdf",
                lines=200
            ),
        ]
    
    def test_init(self, tmp_path):
        """Test orchestrator initialization."""
        orch = SyncOrchestrator(tmp_path)
        assert isinstance(orch.storage, LocalStorage)
        assert orch.storage.base_path == tmp_path
        assert orch.progress is not None
        assert orch.progress.total_projects == 0
        assert orch.progress.completed_projects == 0
    
    @pytest.mark.asyncio
    async def test_sync_all_not_logged_in(self, orchestrator):
        """Test sync when not logged in."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection not logged in
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = False
                
                result = await orchestrator.sync_all()
                
                assert result["success"] is False
                assert "Not logged in" in result["error"]
                mock_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_all_success(self, orchestrator, sample_projects, sample_files):
        """Test successful sync of all projects."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = sample_projects
                mock_connection.extract_knowledge_files.return_value = sample_files
                mock_connection.download_file_content.return_value = "test content"
                
                result = await orchestrator.sync_all()
                
                assert result["success"] is True
                assert result["projects_synced"] == 2
                assert result["files_synced"] == 4  # 2 files per project
                assert len(result["errors"]) == 0
                
                # Verify navigation calls
                mock_connection.navigate.assert_any_call("https://claude.ai/projects")
                mock_connection.navigate.assert_any_call("https://claude.ai/project/1", timeout=90000)
                mock_connection.navigate.assert_any_call("https://claude.ai/project/2", timeout=90000)
                
                # Verify storage was updated
                sync_state = orchestrator.storage.get_sync_state()
                assert sync_state["projects_synced"] == ["Project 1", "Project 2"]
                assert sync_state["total_files"] == 4
    
    @pytest.mark.asyncio
    async def test_sync_all_with_filter(self, orchestrator, sample_projects, sample_files):
        """Test syncing with project filter."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = sample_projects
                mock_connection.extract_knowledge_files.return_value = sample_files
                mock_connection.download_file_content.return_value = "test content"
                
                # Only sync Project 2
                result = await orchestrator.sync_all(filter_projects=["Project 2"])
                
                assert result["success"] is True
                assert result["projects_synced"] == 1
                assert result["files_synced"] == 2
                
                # Should only navigate to Project 2
                mock_connection.navigate.assert_any_call("https://claude.ai/project/2", timeout=90000)
                # Should not navigate to Project 1
                for call in mock_connection.navigate.call_args_list:
                    assert "project/1" not in call[0][0]
    
    @pytest.mark.asyncio
    async def test_sync_project_by_name(self, orchestrator, sample_projects, sample_files):
        """Test syncing project by name."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = sample_projects
                mock_connection.extract_knowledge_files.return_value = sample_files
                mock_connection.download_file_content.return_value = "test content"
                
                result = await orchestrator.sync_project("Project 1")
                
                assert result["success"] is True
                assert result["projects_synced"] == 1
                assert result["files_synced"] == 2
    
    @pytest.mark.asyncio
    async def test_project_with_download_error(self, orchestrator, sample_projects, sample_files):
        """Test handling of download errors."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = sample_projects[:1]  # One project
                mock_connection.extract_knowledge_files.return_value = sample_files
                
                # First download succeeds, second fails
                mock_connection.download_file_content.side_effect = [
                    "test content",
                    None  # Indicates download failure
                ]
                
                # Mock alternative download to also fail
                with patch.object(orchestrator, '_alternative_download', return_value=None):
                    result = await orchestrator.sync_all()
                    
                    assert result["success"] is True  # Overall sync succeeds
                    assert result["projects_synced"] == 1
                    assert result["files_synced"] == 1  # Only one file succeeded
                    assert len(result["errors"]) == 1  # One error recorded
                    assert "file_sync" in result["errors"][0]["type"]
    
    @pytest.mark.asyncio
    async def test_progress_tracking(self, orchestrator, sample_projects, sample_files):
        """Test that progress is tracked correctly."""
        # Track progress updates
        progress_updates = []
        
        def capture_progress():
            progress_updates.append({
                "total_projects": orchestrator.progress.total_projects,
                "completed_projects": orchestrator.progress.completed_projects,
                "total_files": orchestrator.progress.total_files,
                "completed_files": orchestrator.progress.completed_files
            })
        
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = sample_projects
                mock_connection.extract_knowledge_files.return_value = sample_files
                mock_connection.download_file_content.return_value = "test content"
                
                # Patch _update_progress to capture state
                original_update = orchestrator._update_progress
                with patch.object(orchestrator, '_update_progress', side_effect=lambda: (capture_progress(), original_update())):
                    result = await orchestrator.sync_all()
                    
                    assert result["success"] is True
                    
                    # Check that progress was tracked
                    assert len(progress_updates) > 0
                    
                    # Final state should show completion
                    assert orchestrator.progress.total_projects == 2
                    assert orchestrator.progress.completed_projects == 2
                    assert orchestrator.progress.total_files == 4
                    assert orchestrator.progress.completed_files == 4
    
    @pytest.mark.asyncio
    async def test_empty_project_list(self, orchestrator):
        """Test sync with no projects."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = []  # No projects
                
                result = await orchestrator.sync_all()
                
                assert result["success"] is True
                assert result["projects_synced"] == 0
                assert result["files_synced"] == 0
                
                # Should still navigate to projects page
                mock_connection.navigate.assert_called_once_with("https://claude.ai/projects")
    
    @pytest.mark.asyncio
    async def test_project_with_no_files(self, orchestrator, sample_projects):
        """Test syncing project with no knowledge files."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = sample_projects[:1]
                mock_connection.extract_knowledge_files.return_value = []  # No files
                
                result = await orchestrator.sync_all()
                
                assert result["success"] is True
                assert result["projects_synced"] == 1
                assert result["files_synced"] == 0
    
    @pytest.mark.asyncio
    async def test_sync_creates_project_directories(self, orchestrator, sample_projects, sample_files):
        """Test that sync creates proper directory structure."""
        with patch('claude_sync.sync.orchestrator.ChromeManager') as mock_manager_class:
            # Mock manager
            mock_manager = AsyncMock()
            mock_browser = AsyncMock()
            mock_connection = AsyncMock()
            
            mock_manager_class.return_value = mock_manager
            mock_manager.get_or_create_browser.return_value = mock_browser
            
            # Mock connection
            with patch('claude_sync.sync.orchestrator.ChromeConnection') as mock_conn_class:
                mock_conn_class.return_value = mock_connection
                mock_connection.is_logged_in.return_value = True
                mock_connection.extract_projects.return_value = sample_projects[:1]
                mock_connection.extract_knowledge_files.return_value = sample_files[:1]
                mock_connection.download_file_content.return_value = "test content"
                
                result = await orchestrator.sync_all()
                
                assert result["success"] is True
                
                # Verify project directory was created
                project_dir = orchestrator.storage.get_project_path(sample_projects[0])
                assert project_dir.exists()
                
                # Verify knowledge directory exists
                knowledge_dir = project_dir / "knowledge"
                assert knowledge_dir.exists()
                
                # Verify file was saved
                files = list(knowledge_dir.glob("*.text"))
                assert len(files) == 1