#!/usr/bin/env python3
import json
import requests
import time
from websocket import create_connection

def get_projects():
    # Get list of pages
    response = requests.get('http://localhost:9222/json')
    pages = response.json()
    
    print(f"Found {len(pages)} pages\n")
    
    # Find the main Claude page (not iframe)
    claude_page = None
    for i, page in enumerate(pages):
        url = page.get('url', '')
        title = page.get('title', 'No title')
        print(f"{i}: {title[:50]}... - {url[:80]}...")
        
        # Look for main Claude page, not Stripe iframe
        if 'claude.ai' in url and 'stripe' not in url and page.get('type') == 'page':
            claude_page = page
            print(f"  ^ Selected this as Claude main page")
    
    if not claude_page:
        print("\nCould not find Claude page. Please make sure you're on claude.ai")
        return
    
    # Connect to the page via WebSocket
    ws_url = claude_page['webSocketDebuggerUrl']
    print(f"\nConnecting to: {ws_url}")
    
    ws = create_connection(ws_url)
    
    # Enable necessary domains
    ws.send(json.dumps({"id": 1, "method": "Page.enable", "params": {}}))
    ws.send(json.dumps({"id": 2, "method": "Runtime.enable", "params": {}}))
    ws.send(json.dumps({"id": 3, "method": "DOM.enable", "params": {}}))
    
    # Wait a moment
    time.sleep(1)
    
    # First, check current URL
    ws.send(json.dumps({
        "id": 4,
        "method": "Runtime.evaluate",
        "params": {"expression": "window.location.href"}
    }))
    
    current_url = None
    while True:
        result = json.loads(ws.recv())
        if result.get('id') == 4:
            current_url = result.get('result', {}).get('result', {}).get('value', '')
            print(f"\nCurrent URL: {current_url}")
            break
    
    # If not on projects page, navigate there
    if '/projects' not in current_url:
        print("Navigating to projects page...")
        ws.send(json.dumps({
            "id": 5,
            "method": "Page.navigate",
            "params": {"url": "https://claude.ai/projects"}
        }))
        time.sleep(4)  # Wait for navigation
    
    # Try multiple methods to find projects
    print("\nLooking for projects...")
    
    # Method 1: Look for project links
    js_code = '''
    (() => {
        const results = {
            method: "direct links",
            projects: []
        };
        
        // Look for links containing /project/
        const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
        links.forEach(link => {
            const href = link.getAttribute('href');
            const text = link.textContent.trim();
            if (href && text) {
                results.projects.push({
                    name: text,
                    url: href.startsWith('http') ? href : 'https://claude.ai' + href,
                    id: href.match(/project\/([^/?]+)/)?.[1] || 'unknown'
                });
            }
        });
        
        // If no projects found, look for other indicators
        if (results.projects.length === 0) {
            // Check if we're on the projects page
            const isProjectsPage = window.location.pathname === '/projects';
            results.isProjectsPage = isProjectsPage;
            
            // Look for any elements that might contain projects
            const projectElements = document.querySelectorAll('[class*="project" i], [id*="project" i]');
            results.projectElementsFound = projectElements.length;
            
            // Check for "New Project" button as indicator
            const newProjectBtn = document.querySelector('button:has-text("New Project"), button:contains("New Project"), button[aria-label*="project" i]');
            results.hasNewProjectButton = !!newProjectBtn;
        }
        
        return results;
    })()
    '''
    
    ws.send(json.dumps({
        "id": 6,
        "method": "Runtime.evaluate",
        "params": {"expression": js_code}
    }))
    
    # Get results
    projects_data = None
    while True:
        result = json.loads(ws.recv())
        if result.get('id') == 6:
            if 'result' in result and 'result' in result['result']:
                projects_data = result['result']['result'].get('value', {})
                break
    
    if projects_data:
        if projects_data.get('projects'):
            print(f"\nFound {len(projects_data['projects'])} projects:")
            for proj in projects_data['projects']:
                print(f"  - {proj['name']}")
                print(f"    URL: {proj['url']}")
                print(f"    ID: {proj['id']}")
        else:
            print(f"\nNo projects found directly.")
            print(f"On projects page: {projects_data.get('isProjectsPage', False)}")
            print(f"Project elements found: {projects_data.get('projectElementsFound', 0)}")
            print(f"Has 'New Project' button: {projects_data.get('hasNewProjectButton', False)}")
            
            # Try alternative method - look at page structure
            print("\nTrying alternative extraction method...")
            
            alt_js = '''
            (() => {
                // Get all text content and look for project-like patterns
                const pageText = document.body.innerText;
                const hasProjects = pageText.includes('Projects') || pageText.includes('New Project');
                
                // Get page HTML snippet for debugging
                const mainContent = document.querySelector('main, [role="main"], .main-content');
                const htmlSnippet = mainContent ? mainContent.innerHTML.substring(0, 500) : document.body.innerHTML.substring(0, 500);
                
                return {
                    hasProjectsText: hasProjects,
                    htmlSnippet: htmlSnippet,
                    url: window.location.href
                };
            })()
            '''
            
            ws.send(json.dumps({
                "id": 7,
                "method": "Runtime.evaluate", 
                "params": {"expression": alt_js}
            }))
            
            while True:
                result = json.loads(ws.recv())
                if result.get('id') == 7:
                    alt_data = result.get('result', {}).get('result', {}).get('value', {})
                    print(f"\nPage analysis:")
                    print(f"Has projects text: {alt_data.get('hasProjectsText', False)}")
                    print(f"Current URL: {alt_data.get('url', 'unknown')}")
                    print(f"\nHTML snippet (first 500 chars):")
                    print(alt_data.get('htmlSnippet', 'No content found')[:500])
                    break
    
    # Close connection
    ws.close()

if __name__ == "__main__":
    get_projects()