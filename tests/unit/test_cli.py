"""Tests for CLI functionality."""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import argparse

from sync_cli import main, sync_all, sync_project, list_projects


class TestCLI:
    """Test CLI argument parsing and command execution."""
    
    def test_sync_command_with_custom_storage(self, tmp_path, monkeypatch):
        """Test sync command with custom storage directory."""
        custom_storage = tmp_path / "custom_storage"
        
        # Mock sys.argv
        test_args = ['sync_cli.py', 'sync', '--storage', str(custom_storage)]
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # Mock asyncio.run to capture the args
        captured_args = None
        async def mock_sync_all(args):
            nonlocal captured_args
            captured_args = args
            return {"success": True, "projects_synced": 0, "files_synced": 0, "duration_seconds": 0, "errors": []}
        
        with patch('sync_cli.sync_all', mock_sync_all):
            with patch('asyncio.run', lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                main()
        
        assert captured_args is not None
        assert captured_args.storage == str(custom_storage)
        assert captured_args.command == 'sync'
    
    def test_sync_project_command_with_custom_storage(self, tmp_path, monkeypatch):
        """Test sync-project command with custom storage directory."""
        custom_storage = tmp_path / "project_storage"
        
        # Mock sys.argv
        test_args = ['sync_cli.py', 'sync-project', 'TestProject', '--storage', str(custom_storage)]
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # Mock asyncio.run to capture the args
        captured_args = None
        async def mock_sync_project(args):
            nonlocal captured_args
            captured_args = args
            return {"success": True, "files_synced": 0, "duration_seconds": 0}
        
        with patch('sync_cli.sync_project', mock_sync_project):
            with patch('asyncio.run', lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                main()
        
        assert captured_args is not None
        assert captured_args.storage == str(custom_storage)
        assert captured_args.project == 'TestProject'
        assert captured_args.command == 'sync-project'
    
    def test_list_command_with_custom_storage(self, tmp_path, monkeypatch):
        """Test list command with custom storage directory."""
        custom_storage = tmp_path / "list_storage"
        
        # Mock sys.argv
        test_args = ['sync_cli.py', 'list', '--storage', str(custom_storage)]
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # Mock the list function
        captured_args = None
        async def mock_list_projects(args):
            nonlocal captured_args
            captured_args = args
        
        with patch('sync_cli.list_projects', mock_list_projects):
            with patch('asyncio.run', lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                main()
        
        assert captured_args is not None
        assert captured_args.storage == str(custom_storage)
        assert captured_args.command == 'list'
    
    def test_headless_and_quiet_options(self, monkeypatch):
        """Test --headless and --quiet options."""
        # Mock sys.argv
        test_args = ['sync_cli.py', 'sync', '--headless', '--quiet']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # Mock asyncio.run to capture the args
        captured_args = None
        async def mock_sync_all(args):
            nonlocal captured_args
            captured_args = args
            return {"success": True, "projects_synced": 0, "files_synced": 0, "duration_seconds": 0, "errors": []}
        
        with patch('sync_cli.sync_all', mock_sync_all):
            with patch('asyncio.run', lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                main()
        
        assert captured_args is not None
        assert captured_args.headless is True
        assert captured_args.quiet is True
    
    def test_no_command_shows_help(self, monkeypatch, capsys):
        """Test that no command shows help."""
        # Mock sys.argv
        test_args = ['sync_cli.py']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        with pytest.raises(SystemExit):
            main()
        
        captured = capsys.readouterr()
        assert "usage:" in captured.out
        assert "Commands" in captured.out
    
    @pytest.mark.asyncio
    async def test_sync_all_function(self, tmp_path):
        """Test sync_all function with custom storage."""
        custom_storage = tmp_path / "sync_test"
        
        # Create mock args
        args = argparse.Namespace(
            storage=str(custom_storage),
            headless=False,
            quiet=False,
            strict=False
        )
        
        with patch('sync_cli.SyncOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            mock_orchestrator.sync_all = AsyncMock(return_value={
                "success": True,
                "projects_synced": 2,
                "files_synced": 5,
                "duration_seconds": 10.5,
                "errors": []
            })
            
            await sync_all(args)
            
            # Verify orchestrator was created with correct path
            mock_orchestrator_class.assert_called_once()
            call_args = mock_orchestrator_class.call_args[0]
            assert call_args[0] == Path(custom_storage)
    
    @pytest.mark.asyncio
    async def test_sync_project_function(self, tmp_path):
        """Test sync_project function with custom storage."""
        custom_storage = tmp_path / "project_test"
        
        # Create mock args
        args = argparse.Namespace(
            storage=str(custom_storage),
            project="TestProject",
            headless=True,
            quiet=True,
            strict=False
        )
        
        with patch('sync_cli.SyncOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            mock_orchestrator.sync_project = AsyncMock(return_value={
                "success": True,
                "files_synced": 3,
                "duration_seconds": 5.2
            })
            
            await sync_project(args)
            
            # Verify orchestrator was created with correct path
            mock_orchestrator_class.assert_called_once()
            call_args = mock_orchestrator_class.call_args[0]
            assert call_args[0] == Path(custom_storage)
            
            # Verify sync_project was called with correct project name
            mock_orchestrator.sync_project.assert_called_once_with("TestProject")
    
    def test_tilde_expansion(self, monkeypatch):
        """Test that ~ is properly expanded in storage path."""
        # Mock sys.argv with tilde path
        test_args = ['sync_cli.py', 'sync', '--storage', '~/test_storage']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # Mock asyncio.run to capture the args
        captured_args = None
        async def mock_sync_all(args):
            nonlocal captured_args
            captured_args = args
            return {"success": True, "projects_synced": 0, "files_synced": 0, "duration_seconds": 0, "errors": []}
        
        with patch('sync_cli.sync_all', mock_sync_all):
            with patch('asyncio.run', lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                main()
        
        assert captured_args is not None
        # The tilde should still be in the raw argument
        assert captured_args.storage == '~/test_storage'
        # But Path() in the sync functions will expand it
    
    def test_strict_mode_option(self, monkeypatch):
        """Test --strict option is passed correctly."""
        # Mock sys.argv
        test_args = ['sync_cli.py', 'sync', '--strict']
        monkeypatch.setattr(sys, 'argv', test_args)
        
        # Mock asyncio.run to capture the args
        captured_args = None
        async def mock_sync_all(args):
            nonlocal captured_args
            captured_args = args
            return {"success": True, "projects_synced": 0, "files_synced": 0, "duration_seconds": 0, "errors": []}
        
        with patch('sync_cli.sync_all', mock_sync_all):
            with patch('asyncio.run', lambda coro: asyncio.get_event_loop().run_until_complete(coro)):
                main()
        
        assert captured_args is not None
        assert captured_args.strict is True
        assert captured_args.command == 'sync'
    
    @pytest.mark.asyncio
    async def test_sync_all_with_strict_mode_failure(self, tmp_path, capsys):
        """Test sync_all handling of strict mode failure."""
        custom_storage = tmp_path / "strict_test"
        
        # Create mock args
        args = argparse.Namespace(
            storage=str(custom_storage),
            headless=False,
            quiet=False,
            strict=True
        )
        
        # Mock orchestrator to return strict mode failure
        with patch('sync_cli.SyncOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            mock_orchestrator.sync_all = AsyncMock(return_value={
                "success": False,
                "error": "Strict mode: Failed to sync file test.txt in project TestProject",
                "strict_mode_report": {
                    "error": {
                        "file": "test.txt",
                        "project": "TestProject",
                        "error": "Failed to download file content"
                    },
                    "progress_at_failure": {
                        "completed_files": 3,
                        "total_files": 10
                    }
                },
                "report_path": str(custom_storage / ".metadata" / "strict_mode_failure.json")
            })
            
            with pytest.raises(SystemExit) as exc_info:
                await sync_all(args)
            
            assert exc_info.value.code == 1
            
            # Check output includes strict mode report
            captured = capsys.readouterr()
            assert "Strict Mode Failure Report" in captured.out
            assert "test.txt" in captured.out
            assert "TestProject" in captured.out