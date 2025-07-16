#!/usr/bin/env python3
"""Test script to verify Claude Sync installation."""
import sys
import asyncio

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import playwright
        print("✓ playwright")
    except ImportError:
        print("✗ playwright - Run: pip install playwright")
        return False
    
    try:
        import pydantic
        print("✓ pydantic")
    except ImportError:
        print("✗ pydantic - Run: pip install pydantic")
        return False
    
    try:
        import bs4
        print("✓ beautifulsoup4")
    except ImportError:
        print("✗ beautifulsoup4 - Run: pip install beautifulsoup4")
        return False
    
    try:
        import aiofiles
        print("✓ aiofiles")
    except ImportError:
        print("✗ aiofiles - Run: pip install aiofiles")
        return False
    
    try:
        from claude_sync import SyncOrchestrator
        from claude_sync.browser import BrowserConfig, ChromeManager
        from claude_sync.models import Project, KnowledgeFile
        print("✓ claude_sync modules")
    except ImportError as e:
        print(f"✗ claude_sync modules - Error: {e}")
        return False
    
    return True


async def test_chrome_connection():
    """Test Chrome connection."""
    print("\nTesting Chrome connection...")
    
    try:
        from claude_sync.browser import ChromeManager, BrowserConfig
        
        config = BrowserConfig(port=9222)
        manager = ChromeManager(config)
        
        try:
            browser = await manager.get_or_create_browser()
            print("✓ Connected to Chrome")
            # Note: browser is a BrowserContext, not Browser object
            return True
        except Exception as e:
            print(f"✗ Could not connect to Chrome: {e}")
            print("\nMake sure Chrome is running with:")
            print("  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
            return False
        finally:
            await manager.close()
            
    except Exception as e:
        print(f"✗ Error testing Chrome: {e}")
        return False


async def test_claude_login():
    """Test Claude.ai login status."""
    print("\nTesting Claude.ai login...")
    
    try:
        from claude_sync.browser import ChromeManager, BrowserConfig, ChromeConnection
        
        config = BrowserConfig(port=9222)
        manager = ChromeManager(config)
        
        try:
            browser = await manager.get_or_create_browser()
            connection = ChromeConnection(browser)
            
            if await connection.is_logged_in():
                print("✓ Logged in to Claude.ai")
                
                # Try to get projects
                await connection.navigate("https://claude.ai/projects")
                await asyncio.sleep(3)
                
                projects = await connection.extract_projects()
                print(f"✓ Found {len(projects)} projects")
                
                return True
            else:
                print("✗ Not logged in to Claude.ai")
                print("\nPlease log in to Claude.ai in the Chrome window")
                return False
                
        finally:
            await manager.close()
            
    except Exception as e:
        print(f"✗ Error testing Claude login: {e}")
        return False


async def main():
    """Run all tests."""
    print("Claude Sync Installation Test")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        print("\nPlease install missing dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    
    # Test Chrome connection
    if not await test_chrome_connection():
        sys.exit(1)
    
    # Test Claude login
    if not await test_claude_login():
        sys.exit(1)
    
    print("\n" + "=" * 40)
    print("✓ All tests passed! Claude Sync is ready to use.")
    print("\nTry running:")
    print("  python sync_cli.py list")
    print("  python sync_cli.py sync-project \"Your Project Name\"")


if __name__ == "__main__":
    asyncio.run(main())