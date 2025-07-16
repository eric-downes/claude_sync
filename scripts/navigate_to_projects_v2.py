#!/usr/bin/env python3
import json
import requests
import time
from websocket import create_connection

def navigate_to_projects():
    # Get list of pages
    response = requests.get('http://localhost:9222/json')
    pages = response.json()
    
    print(f"Found {len(pages)} pages")
    
    # Find the Claude page
    claude_page = None
    for page in pages:
        print(f"Page: {page.get('title', 'No title')} - {page.get('url', 'No URL')}")
        if 'claude.ai' in page.get('url', ''):
            claude_page = page
            break
    
    if not claude_page:
        print("Could not find Claude page")
        return
    
    # Connect to the page via WebSocket
    ws_url = claude_page['webSocketDebuggerUrl']
    print(f"\nConnecting to: {ws_url}")
    
    ws = create_connection(ws_url)
    
    # Enable necessary domains
    ws.send(json.dumps({"id": 1, "method": "Page.enable", "params": {}}))
    ws.send(json.dumps({"id": 2, "method": "Runtime.enable", "params": {}}))
    
    # Navigate to projects
    print("\nNavigating to projects page...")
    ws.send(json.dumps({
        "id": 3,
        "method": "Page.navigate",
        "params": {"url": "https://claude.ai/projects"}
    }))
    
    # Wait for navigation
    time.sleep(3)
    
    # Get current URL
    ws.send(json.dumps({
        "id": 4,
        "method": "Runtime.evaluate",
        "params": {"expression": "window.location.href"}
    }))
    
    # Read responses
    while True:
        result = json.loads(ws.recv())
        if result.get('id') == 4:
            current_url = result.get('result', {}).get('result', {}).get('value', '')
            print(f"Current URL: {current_url}")
            break
    
    # Wait for content to load
    time.sleep(2)
    
    # Try to get project information
    print("\nLooking for projects...")
    
    # More specific selector for project links
    js_code = '''
    (() => {
        // Try multiple selectors
        const projectLinks = document.querySelectorAll('a[href*="/project/"], [data-testid*="project"], .project-item');
        const projects = [];
        
        projectLinks.forEach(element => {
            const href = element.href || element.querySelector('a')?.href;
            const text = element.textContent?.trim() || element.querySelector('[class*="title"]')?.textContent?.trim();
            if (href && href.includes('/project/')) {
                projects.push({text: text || 'Untitled', href: href});
            }
        });
        
        // Also check for any divs/sections that might contain projects
        if (projects.length === 0) {
            const possibleContainers = document.querySelectorAll('[class*="project"], [id*="project"]');
            console.log(`Found ${possibleContainers.length} possible project containers`);
        }
        
        return projects;
    })()
    '''
    
    ws.send(json.dumps({
        "id": 5,
        "method": "Runtime.evaluate",
        "params": {"expression": js_code}
    }))
    
    # Get the result
    while True:
        result = json.loads(ws.recv())
        if result.get('id') == 5:
            if 'result' in result and 'result' in result['result']:
                projects = result['result']['result'].get('value', [])
                if projects:
                    print(f"\nFound {len(projects)} projects:")
                    for proj in projects:
                        print(f"  - {proj['text']}: {proj['href']}")
                else:
                    print("No projects found. Page might still be loading or structure changed.")
            break
    
    # Close connection
    ws.close()

if __name__ == "__main__":
    navigate_to_projects()