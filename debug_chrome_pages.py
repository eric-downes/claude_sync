#!/usr/bin/env python3
"""
Debug script to see all Chrome pages and help find Claude.ai
"""
import requests
import json


def debug_chrome_pages():
    """Show all Chrome pages to help debug connection issues."""
    try:
        # Get all pages from Chrome
        response = requests.get('http://localhost:9222/json')
        pages = response.json()
        
        print(f"\nFound {len(pages)} Chrome pages/tabs:\n")
        print("-" * 80)
        
        for i, page in enumerate(pages):
            url = page.get('url', 'No URL')
            title = page.get('title', 'No title')
            page_type = page.get('type', 'unknown')
            ws_url = page.get('webSocketDebuggerUrl', 'No WebSocket URL')
            
            print(f"Page {i + 1}:")
            print(f"  Title: {title[:60]}...")
            print(f"  URL: {url}")
            print(f"  Type: {page_type}")
            print(f"  WebSocket: {ws_url}")
            
            # Highlight Claude pages
            if 'claude.ai' in url:
                print(f"  >>> THIS IS A CLAUDE PAGE! <<<")
                if 'stripe' in url:
                    print(f"  >>> (But it's a Stripe iframe - not the main page)")
            
            print("-" * 80)
        
        # Look for Claude pages specifically
        claude_pages = [p for p in pages if 'claude.ai' in p.get('url', '')]
        if claude_pages:
            print(f"\nFound {len(claude_pages)} Claude.ai related pages:")
            for cp in claude_pages:
                print(f"  - {cp.get('url')}")
        else:
            print("\n❌ No Claude.ai pages found!")
            print("\nPossible issues:")
            print("1. Chrome might not be running with --remote-debugging-port=9222")
            print("2. The Claude.ai tab might not be open")
            print("3. You might need to refresh the Claude.ai page")
            
    except requests.ConnectionError:
        print("❌ Cannot connect to Chrome on localhost:9222")
        print("\nMake sure Chrome is running with:")
        print("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --remote-allow-origins='*'")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    debug_chrome_pages()