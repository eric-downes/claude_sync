#!/usr/bin/env python3
"""Debug project extraction issue."""
import json
from src.chrome.robust_client import RobustChromeClient

def main():
    print("Debugging Project Extraction")
    print("=" * 60)
    
    with RobustChromeClient() as client:
        pages = client.get_pages()
        claude_page = None
        
        for page in pages:
            if 'claude.ai' in page.get('url', ''):
                claude_page = page
                break
        
        if not claude_page:
            print("❌ No Claude.ai page found")
            return 1
        
        print(f"✓ Connected to: {claude_page.get('url', '')}")
        client.connect_to_page(claude_page)
        
        # Check current URL
        current_url = client.evaluate_expression("window.location.href")
        print(f"✓ Current URL: {current_url}")
        
        # Check for project links
        print("\n🔍 Checking for project links...")
        
        # Method 1: Direct selector check
        link_count = client.evaluate_expression("""
            document.querySelectorAll('a[href*="/project/"]').length
        """)
        print(f"  Project links found: {link_count}")
        
        # Method 2: Get first few links
        first_links = client.evaluate_expression("""
            JSON.stringify(
                Array.from(document.querySelectorAll('a[href*="/project/"]'))
                    .slice(0, 3)
                    .map(a => ({
                        href: a.href,
                        text: a.textContent.trim().substring(0, 50)
                    }))
            )
        """)
        
        if first_links:
            print("\n  First few project links:")
            for link in first_links:
                print(f"    - {link['text']}...")
                print(f"      {link['href']}")
        
        # Check page content
        print("\n📄 Page content check:")
        body_text = client.evaluate_expression("document.body.innerText.substring(0, 200)")
        print(f"  Body text: {body_text}...")
        
        # Check for loading indicators
        loading = client.evaluate_expression("""
            !!document.querySelector('[class*="loading"], [class*="spinner"], [class*="skeleton"]')
        """)
        print(f"\n  Loading indicators present: {loading}")
        
        # Try alternative selectors
        print("\n🔍 Trying alternative selectors...")
        alternatives = client.evaluate_expression("""
            JSON.stringify({
                byRole: document.querySelectorAll('a[role="link"]').length,
                byHref: document.querySelectorAll('a[href^="/project/"]').length,
                allLinks: document.querySelectorAll('a').length,
                withProjectText: Array.from(document.querySelectorAll('a')).filter(a => 
                    a.textContent.includes('Updated') && a.textContent.includes('ago')
                ).length
            })
        """)
        
        print(f"  Links by role: {alternatives['byRole']}")
        print(f"  Links starting with /project/: {alternatives['byHref']}")
        print(f"  Total links: {alternatives['allLinks']}")
        print(f"  Links with 'Updated...ago': {alternatives['withProjectText']}")
        
        # Get actual link hrefs
        all_hrefs = client.evaluate_expression("""
            JSON.stringify(
                Array.from(document.querySelectorAll('a'))
                    .map(a => a.href)
                    .filter(h => h && h.includes('claude.ai'))
                    .slice(0, 10)
            )
        """)
        
        print("\n  Sample hrefs:")
        for href in all_hrefs:
            print(f"    - {href}")
    
    return 0

if __name__ == "__main__":
    main()