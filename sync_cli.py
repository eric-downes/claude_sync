#!/usr/bin/env python3
"""CLI for syncing Claude.ai data."""
import asyncio
import logging
import sys
from pathlib import Path
import argparse
from datetime import datetime

from claude_sync.sync import SyncOrchestrator
from claude_sync.browser import BrowserConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def progress_callback(progress):
    """Print progress updates."""
    if progress.current_file:
        print(f"\r[{progress.completed_files}/{progress.total_files}] "
              f"{progress.current_project}: {progress.current_file}",
              end='', flush=True)
    else:
        print(f"\r[{progress.completed_projects}/{progress.total_projects}] "
              f"Syncing: {progress.current_project or 'Loading...'}",
              end='', flush=True)


async def sync_all(args):
    """Sync all projects."""
    storage_path = Path(args.storage or "claude_sync_data")
    logger.info(f"Storage path: {storage_path}")
    
    config = BrowserConfig(headless=args.headless)
    orchestrator = SyncOrchestrator(
        storage_path,
        browser_config=config,
        progress_callback=progress_callback if not args.quiet else None
    )
    
    print("Starting sync...")
    result = await orchestrator.sync_all()
    print()  # New line after progress
    
    if result["success"]:
        print(f"\n✓ Sync completed successfully!")
        print(f"  Projects synced: {result['projects_synced']}")
        print(f"  Files synced: {result['files_synced']}")
        print(f"  Duration: {result['duration_seconds']:.1f}s")
        
        if result["errors"]:
            print(f"\n⚠ {len(result['errors'])} errors occurred:")
            for error in result["errors"][:5]:  # Show first 5 errors
                print(f"  - {error['type']}: {error.get('file', error.get('project'))}")
    else:
        print(f"\n✗ Sync failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


async def sync_project(args):
    """Sync a specific project."""
    storage_path = Path(args.storage or "claude_sync_data")
    logger.info(f"Storage path: {storage_path}")
    
    config = BrowserConfig(headless=args.headless)
    orchestrator = SyncOrchestrator(
        storage_path,
        browser_config=config,
        progress_callback=progress_callback if not args.quiet else None
    )
    
    print(f"Syncing project: {args.project}")
    result = await orchestrator.sync_project(args.project)
    print()  # New line after progress
    
    if result["success"]:
        print(f"\n✓ Project synced successfully!")
        print(f"  Files synced: {result['files_synced']}")
        print(f"  Duration: {result['duration_seconds']:.1f}s")
    else:
        print(f"\n✗ Sync failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


async def list_projects(args):
    """List synced projects."""
    storage_path = Path(args.storage or "claude_sync_data")
    
    config = BrowserConfig(headless=args.headless)
    orchestrator = SyncOrchestrator(storage_path, browser_config=config)
    
    status = orchestrator.get_sync_status()
    
    print(f"\nSync Status:")
    print(f"  Last sync: {status['last_sync'] or 'Never'}")
    print(f"  Total projects: {status['total_projects']}")
    print(f"  Total files: {status['total_files']}")
    
    if status['synced_projects']:
        print(f"\nSynced Projects:")
        for project in status['synced_projects']:
            last_synced = project.get('last_synced', 'Unknown')
            if last_synced != 'Unknown':
                # Parse and format date
                dt = datetime.fromisoformat(last_synced)
                last_synced = dt.strftime("%Y-%m-%d %H:%M")
            
            print(f"  - {project['name']}")
            print(f"    Last synced: {last_synced}")
            print(f"    Local path: {project['local_path']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Sync Claude.ai data locally")
    parser.add_argument(
        "--storage",
        help="Storage directory (default: claude_sync_data)",
        default="claude_sync_data"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Sync all command
    sync_all_parser = subparsers.add_parser("sync", help="Sync all projects")
    
    # Sync project command
    sync_project_parser = subparsers.add_parser(
        "sync-project",
        help="Sync a specific project"
    )
    sync_project_parser.add_argument("project", help="Project name to sync")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List synced projects")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run appropriate command
    if args.command == "sync":
        asyncio.run(sync_all(args))
    elif args.command == "sync-project":
        asyncio.run(sync_project(args))
    elif args.command == "list":
        asyncio.run(list_projects(args))


if __name__ == "__main__":
    main()