#!/usr/bin/env python3
import json
import requests
import time
from websocket import create_connection

def get_projects_from_existing_tab():
    # Get list of pages
    response = requests.get('http://localhost:9222/json')
    pages = response.json()
    
    print(f"Found {len(pages)} pages\n")
    
    # Find the projects page directly
    projects_page = None
    for i, page in enumerate(pages):
        url = page.get('url', '')
        title = page.get('title', 'No title')
        
        if 'claude.ai/projects' in url:
            projects_page = page
            print(f"Found projects page at index {i}: {title} - {url}")
            break
    
    if not projects_page:
        print("No projects page found. Please navigate to https://claude.ai/projects")
        return
    
    # Connect to the page via WebSocket
    ws_url = projects_page['webSocketDebuggerUrl']
    print(f"\nConnecting to: {ws_url}")
    
    ws = create_connection(ws_url)
    
    # Enable necessary domains
    ws.send(json.dumps({"id": 1, "method": "Runtime.enable", "params": {}}))
    
    # Wait a moment for page to be ready
    time.sleep(1)
    
    # Extract projects using a more robust approach
    js_code = '''
    (() => {
        const results = {
            projects: [],
            debug: {}
        };
        
        // Method 1: Direct link search
        const projectLinks = document.querySelectorAll('a[href*="/project/"]');
        projectLinks.forEach(link => {
            const href = link.getAttribute('href');
            const text = link.textContent.trim();
            if (href && text) {
                results.projects.push({
                    name: text,
                    url: href.startsWith('http') ? href : 'https://claude.ai' + href,
                    id: href.match(/project\\/([^/?]+)/)?.[1] || 'unknown'
                });
            }
        });
        
        // Method 2: Look for project cards/items
        if (results.projects.length === 0) {
            // Common patterns for project items
            const selectors = [
                '[data-testid*="project"]',
                '[class*="project-card"]',
                '[class*="project-item"]',
                '[class*="ProjectCard"]',
                '[class*="ProjectItem"]',
                'article',
                '[role="article"]',
                '.card',
                'li:has(a[href*="/project/"])'
            ];
            
            selectors.forEach(selector => {
                try {
                    const items = document.querySelectorAll(selector);
                    if (items.length > 0) {
                        results.debug[selector] = items.length;
                        items.forEach(item => {
                            const link = item.querySelector('a[href*="/project/"]');
                            if (link) {
                                const href = link.getAttribute('href');
                                const text = link.textContent.trim() || 
                                           item.querySelector('h2, h3, [class*="title"]')?.textContent.trim() ||
                                           'Untitled Project';
                                
                                if (href && !results.projects.find(p => p.url.includes(href))) {
                                    results.projects.push({
                                        name: text,
                                        url: href.startsWith('http') ? href : 'https://claude.ai' + href,
                                        id: href.match(/project\\/([^/?]+)/)?.[1] || 'unknown'
                                    });
                                }
                            }
                        });
                    }
                } catch (e) {}
            });
        }
        
        // Get page info for debugging
        results.debug.url = window.location.href;
        results.debug.title = document.title;
        results.debug.hasNewProjectButton = !!document.querySelector('button:has-text("New Project"), button[aria-label*="new project" i]');
        
        // Get a sample of the page structure
        const main = document.querySelector('main, [role="main"], #main-content');
        if (main) {
            results.debug.mainHTML = main.innerHTML.substring(0, 300);
        }
        
        return results;
    })()
    '''
    
    ws.send(json.dumps({
        "id": 2,
        "method": "Runtime.evaluate",
        "params": {"expression": js_code}
    }))
    
    # Get results
    while True:
        result = json.loads(ws.recv())
        if result.get('id') == 2:
            if 'result' in result and 'result' in result['result']:
                data = result['result']['result'].get('value', {})
                
                print(f"\nDebug info:")
                debug = data.get('debug', {})
                print(f"URL: {debug.get('url', 'unknown')}")
                print(f"Title: {debug.get('title', 'unknown')}")
                print(f"Has 'New Project' button: {debug.get('hasNewProjectButton', False)}")
                
                if data.get('projects'):
                    print(f"\n✅ Found {len(data['projects'])} projects:")
                    for proj in data['projects']:
                        print(f"\n  📁 {proj['name']}")
                        print(f"     URL: {proj['url']}")
                        print(f"     ID: {proj['id']}")
                else:
                    print("\n❌ No projects found")
                    print("\nElement counts by selector:")
                    for selector, count in debug.items():
                        if selector not in ['url', 'title', 'hasNewProjectButton', 'mainHTML']:
                            print(f"  {selector}: {count}")
                    
                    if 'mainHTML' in debug:
                        print(f"\nMain content HTML sample:")
                        print(debug['mainHTML'])
                
                # Save projects data
                if data.get('projects'):
                    with open('found_projects.json', 'w') as f:
                        json.dump(data['projects'], f, indent=2)
                    print(f"\n💾 Saved {len(data['projects'])} projects to found_projects.json")
                
                break
    
    # Close connection
    ws.close()

if __name__ == "__main__":
    get_projects_from_existing_tab()