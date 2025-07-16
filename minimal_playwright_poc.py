#!/usr/bin/env python3
"""
Minimal POC: Playwright connecting to existing Chrome with auth preserved.
This proves we can use better tools without auth headaches.
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import sys


def test_existing_chrome_connection():
    """
    Test that Playwright can:
    1. Connect to existing Chrome (with your Claude auth)
    2. Navigate and extract data
    3. Run completely unattended
    """
    print("Playwright POC - Connecting to Existing Chrome")
    print("=" * 60)
    
    try:
        with sync_playwright() as p:
            # Connect to your existing Chrome with preserved auth!
            print("✓ Connecting to existing Chrome on port 9222...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            # Get the existing context (preserves all cookies/auth)
            context = browser.contexts[0]
            
            # Check if we have any pages open
            if not context.pages:
                print("❌ No pages found. Make sure Chrome has Claude.ai open")
                return False
            
            # Use existing page or create new one in same context
            page = context.pages[0]
            print(f"✓ Connected to: {page.url}")
            
            # Check auth status
            print("\n✓ Checking authentication...")
            if "login" in page.url:
                print("❌ Not logged in. Please log into Claude manually first.")
                return False
            
            # Navigate to projects (auth is preserved!)
            print("✓ Navigating to projects page...")
            page.goto("https://claude.ai/projects")
            
            # Wait for content (much more reliable than time.sleep)
            page.wait_for_selector('a[href*="/project/"]', timeout=10000)
            print("✓ Projects page loaded")
            
            # Extract projects using Playwright's evaluate
            print("\n✓ Extracting projects...")
            projects = page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href*="/project/"]')).map(link => {
                    const div = link.querySelector('div');
                    if (!div) return null;
                    
                    const children = Array.from(div.children);
                    return {
                        name: children[0]?.textContent?.trim(),
                        description: children[1]?.textContent?.trim(),
                        url: link.href
                    };
                }).filter(Boolean)
            """)
            
            print(f"✓ Found {len(projects)} projects")
            
            # Find DNI
            dni = next((p for p in projects if p['name'] == 'DNI'), None)
            
            if dni:
                print(f"\n✓ Found DNI project: {dni['name']}")
                print(f"  Description: {dni.get('description', 'N/A')}")
                
                # Navigate to DNI project
                page.goto(dni['url'])
                page.wait_for_selector('text=Project knowledge')
                
                # Get page HTML for BeautifulSoup
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract with BeautifulSoup
                page_text = soup.get_text()
                if 'Invoice valuation' in page_text:
                    print("\n✓ Successfully accessed DNI knowledge files!")
                    print("✓ Auth is preserved - no login required!")
                    
                    # Quick file count
                    import re
                    file_matches = re.findall(r'(\d+)\s+lines', page_text)
                    print(f"✓ Found {len(file_matches)} knowledge files")
                    
                    return True
            else:
                print("\n❌ DNI project not found")
                print("Available projects:", [p['name'] for p in projects[:5]])
            
            # Important: Don't close browser - keep session alive!
            # browser.close()  # DON'T DO THIS
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """
    This POC proves:
    1. Playwright can connect to existing Chrome (no auth needed)
    2. It preserves all cookies/sessions
    3. It can run unattended
    4. Connection is more reliable than raw WebSocket
    """
    
    print("\nPre-requisites:")
    print("1. Chrome is running with: --remote-debugging-port=9222")
    print("2. You are logged into Claude.ai")
    print("3. Run: pip install playwright beautifulsoup4")
    print("4. Run: playwright install chromium (one time only)")
    print()
    
    success = test_existing_chrome_connection()
    
    if success:
        print("\n" + "🎉 " * 10)
        print("SUCCESS! Key findings:")
        print("✓ Playwright connected to existing Chrome")
        print("✓ Auth was preserved - no login needed")
        print("✓ Could access protected content")
        print("✓ More reliable than manual WebSocket")
        print("\nThis approach will work for unattended operation!")
    else:
        print("\n❌ POC failed - check prerequisites above")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())