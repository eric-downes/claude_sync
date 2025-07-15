#!/usr/bin/env python3
import pychrome
import time
import json

def navigate_to_projects():
    # Create a browser instance
    browser = pychrome.Browser(url="http://127.0.0.1:9222")
    
    # Get all tabs
    tabs = browser.list_tab()
    print(f"Found {len(tabs)} tabs")
    
    # Find the Claude tab
    claude_tab = None
    for tab in tabs:
        # Tab objects have attributes, not dict keys
        print(f"Tab: {tab.title} - {tab.url}")
        if 'claude.ai' in tab.url:
            claude_tab = tab
            break
    
    if not claude_tab:
        print("Could not find Claude tab")
        return
    
    # Create a tab instance
    tab = browser.create_tab(claude_tab.id)
    
    # Start the tab
    tab.start()
    
    # Enable Page domain
    tab.Page.enable()
    
    # Navigate to projects page
    print("Navigating to projects page...")
    tab.Page.navigate(url="https://claude.ai/projects")
    
    # Wait for navigation
    time.sleep(3)
    
    # Get the current URL
    result = tab.Runtime.evaluate(expression="window.location.href")
    print(f"Current URL: {result['result']['value']}")
    
    # Try to get project list
    print("\nTrying to get project information...")
    
    # Wait a bit more for content to load
    time.sleep(2)
    
    # Try to extract project links
    js_code = '''
    Array.from(document.querySelectorAll('a')).
        filter(a => a.href && a.href.includes('/project/')).
        map(a => ({
            text: a.textContent.trim(),
            href: a.href
        }))
    '''
    
    result = tab.Runtime.evaluate(expression=js_code)
    if 'result' in result and 'value' in result['result']:
        projects = result['result']['value']
        print(f"\nFound {len(projects)} projects:")
        for proj in projects:
            print(f"  - {proj['text']}: {proj['href']}")
    
    # Close the tab connection
    tab.stop()

if __name__ == "__main__":
    navigate_to_projects()