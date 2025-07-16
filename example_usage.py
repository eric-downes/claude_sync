#!/usr/bin/env python3
"""Example usage of Claude Sync."""
import asyncio
from pathlib import Path

from claude_sync.sync import SyncOrchestrator
from claude_sync.browser import BrowserConfig


def progress_callback(progress):
    """Custom progress callback."""
    print(f"\rProgress: {progress.completed_files}/{progress.total_files} files "
          f"({progress.progress_percent:.1f}%)", end='', flush=True)


async def example_sync():
    """Example of programmatic usage."""
    
    # Configure storage location
    storage_path = Path("my_claude_backup")
    
    # Configure browser (optional)
    browser_config = BrowserConfig(
        headless=False,  # Set to True for background operation
        port=9222        # Chrome DevTools port
    )
    
    # Create orchestrator
    orchestrator = SyncOrchestrator(
        storage_path=storage_path,
        browser_config=browser_config,
        progress_callback=progress_callback
    )
    
    # Example 1: Sync all projects
    print("Syncing all projects...")
    result = await orchestrator.sync_all()
    
    if result["success"]:
        print(f"\n✓ Synced {result['projects_synced']} projects with {result['files_synced']} files")
    else:
        print(f"\n✗ Sync failed: {result['error']}")
    
    # Example 2: Sync specific projects
    print("\n\nSyncing specific project...")
    result = await orchestrator.sync_project("My Important Project")
    
    # Example 3: Get sync status
    print("\n\nCurrent sync status:")
    status = orchestrator.get_sync_status()
    print(f"  Last sync: {status['last_sync']}")
    print(f"  Total projects: {status['total_projects']}")
    print(f"  Total files: {status['total_files']}")
    
    # Example 4: List synced projects
    print("\n\nSynced projects:")
    for project in status['synced_projects']:
        print(f"  - {project['name']}")
        print(f"    Path: {project['local_path']}")


async def example_custom_sync():
    """Example with custom filtering."""
    
    orchestrator = SyncOrchestrator(Path("filtered_backup"))
    
    # Sync only specific projects
    projects_to_sync = ["Project A", "Project B", "Important Research"]
    
    result = await orchestrator.sync_all(filter_projects=projects_to_sync)
    
    print(f"Synced {result['projects_synced']} projects")


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_sync())
    
    # Uncomment to run custom sync example
    # asyncio.run(example_custom_sync())