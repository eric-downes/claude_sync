#!/usr/bin/env python3
"""
Manual test for ChromeClient - requires Chrome running with debug port.

To run:
1. Start Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --remote-allow-origins='*'
2. Navigate to https://claude.ai and login
3. Run this script: python manual_test_chrome_client.py
"""
import sys
from src.chrome.client import ChromeClient
from src.chrome.exceptions import ChromeNotFoundError, ChromePageNotFoundError


def test_chrome_connection():
    """Test connecting to Chrome and finding Claude page."""
    print("Testing Chrome connection...")
    
    try:
        client = ChromeClient()
        
        # Test 1: Get pages
        print("\n1. Getting Chrome pages...")
        pages = client.get_pages()
        print(f"   ✓ Found {len(pages)} pages")
        
        for i, page in enumerate(pages[:5]):  # Show first 5 pages
            print(f"   - {page.get('title', 'No title')[:50]}...")
        
        # Test 2: Find Claude page
        print("\n2. Looking for Claude page...")
        try:
            claude_page = client.find_claude_page()
            print(f"   ✓ Found Claude page: {claude_page.get('url')}")
        except ChromePageNotFoundError as e:
            print(f"   ✗ {e}")
            print("   Please navigate to claude.ai in Chrome")
            return False
        
        # Test 3: Connect via WebSocket
        print("\n3. Connecting via WebSocket...")
        with client:
            print("   ✓ WebSocket connection established")
            
            # Test 4: Send a command
            print("\n4. Testing command execution...")
            result = client.send_command("Runtime.evaluate", {
                "expression": "window.location.href"
            })
            current_url = result.get('result', {}).get('value', 'unknown')
            print(f"   ✓ Current URL: {current_url}")
            
            # Test 5: Navigation (optional - uncomment to test)
            # print("\n5. Testing navigation...")
            # client.navigate_to("https://claude.ai/projects")
            # print("   ✓ Navigated to projects page")
        
        print("\n✅ All tests passed!")
        return True
        
    except ChromeNotFoundError as e:
        print(f"\n❌ Chrome not found: {e}")
        print("\nPlease start Chrome with:")
        print("  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --remote-allow-origins='*'")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_chrome_connection()
    sys.exit(0 if success else 1)