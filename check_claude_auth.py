#!/usr/bin/env python3
"""Check Claude authentication status."""
import requests

try:
    response = requests.get('http://localhost:9222/json', timeout=2)
    pages = response.json()
    
    print("Current Chrome pages:")
    print("=" * 60)
    for i, page in enumerate(pages):
        url = page.get('url', '')
        title = page.get('title', 'Untitled')
        print(f"{i+1}. {title}")
        print(f"   URL: {url}")
        
        if 'login' in url:
            print("   ⚠️  LOGIN REQUIRED - Please log into Claude.ai")
        elif 'claude.ai' in url:
            print("   ✓ Claude.ai page")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    if any('login' in p.get('url', '') for p in pages):
        print("1. Go to the Chrome window that opened")
        print("2. Log into Claude.ai with your account")
        print("3. Once logged in, run: python test_dni_knowledge_titles.py")
    else:
        print("Chrome is ready. Run: python test_dni_knowledge_titles.py")
        
except Exception as e:
    print(f"Error: {e}")
    print("Make sure Chrome is running with --remote-debugging-port=9222")