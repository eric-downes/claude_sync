#!/usr/bin/env python3
import json
import requests
import time
from websocket import create_connection

def debug_projects_page():
    # Get list of pages
    response = requests.get('http://localhost:9222/json')
    pages = response.json()
    
    # Find the projects page
    projects_page = None
    for page in pages:
        if 'claude.ai/projects' in page.get('url', ''):
            projects_page = page
            print(f"Found projects page: {page['url']}")
            break
    
    if not projects_page:
        print("No projects page found")
        return
    
    ws = create_connection(projects_page['webSocketDebuggerUrl'])
    
    # Enable Runtime
    ws.send(json.dumps({"id": 1, "method": "Runtime.enable", "params": {}}))
    time.sleep(0.5)
    
    # Get basic page info
    ws.send(json.dumps({
        "id": 2,
        "method": "Runtime.evaluate",
        "params": {
            "expression": '''({
                url: window.location.href,
                title: document.title,
                readyState: document.readyState,
                bodyText: document.body.innerText.substring(0, 500),
                linkCount: document.querySelectorAll('a').length,
                projectLinks: Array.from(document.querySelectorAll('a')).filter(a => a.href.includes('/project/')).map(a => ({
                    text: a.textContent.trim(),
                    href: a.href
                }))
            })'''
        }
    }))
    
    # Get response
    while True:
        result = json.loads(ws.recv())
        if result.get('id') == 2:
            if 'result' in result and 'result' in result['result']:
                data = result['result']['result'].get('value', {})
                print(f"\nPage Info:")
                print(f"URL: {data.get('url', 'unknown')}")
                print(f"Title: {data.get('title', 'unknown')}")
                print(f"Ready State: {data.get('readyState', 'unknown')}")
                print(f"Total links: {data.get('linkCount', 0)}")
                
                print(f"\nBody text (first 500 chars):")
                print(data.get('bodyText', 'No text found'))
                
                project_links = data.get('projectLinks', [])
                if project_links:
                    print(f"\n✅ Found {len(project_links)} project links:")
                    for link in project_links:
                        print(f"  - {link['text']}: {link['href']}")
                else:
                    print("\n❌ No project links found")
            break
    
    ws.close()

if __name__ == "__main__":
    debug_projects_page()