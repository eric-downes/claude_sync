#!/usr/bin/env python3
"""
Example of improved implementation using BeautifulSoup and better CDP libraries.
This shows how the code would be cleaner and more reliable.
"""

# Example 1: Using PyChromeDevTools + BeautifulSoup
from PyChromeDevTools import ChromeInterface
from bs4 import BeautifulSoup
import time

def extract_dni_files_improved():
    # Much cleaner connection
    chrome = ChromeInterface()
    chrome.connect()
    
    # Navigate to projects
    chrome.Page.navigate(url="https://claude.ai/projects")
    time.sleep(2)
    
    # Get page HTML directly
    result = chrome.Runtime.evaluate(expression="document.documentElement.outerHTML")
    html = result['result']['value']
    
    # Use BeautifulSoup for parsing - MUCH cleaner!
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all project links
    project_links = soup.find_all('a', href=lambda x: x and '/project/' in x)
    
    # Extract projects with proper structure
    projects = []
    for link in project_links:
        # BeautifulSoup makes this so much easier
        project_div = link.find('div')
        if project_div:
            children = list(project_div.children)
            if len(children) >= 2:
                title_div = children[0]
                desc_div = children[1]
                
                project = {
                    'name': title_div.get_text(strip=True),
                    'description': desc_div.get_text(strip=True) if 'Updated' not in desc_div.get_text() else None,
                    'url': link['href']
                }
                projects.append(project)
    
    # Find DNI project
    dni_project = next((p for p in projects if p['name'] == 'DNI'), None)
    
    if dni_project:
        # Navigate to project
        chrome.Page.navigate(url=f"https://claude.ai{dni_project['url']}")
        time.sleep(2)
        
        # Get project page HTML
        result = chrome.Runtime.evaluate(expression="document.documentElement.outerHTML")
        html = result['result']['value']
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract knowledge files - much cleaner with BeautifulSoup
        page_text = soup.get_text()
        lines = page_text.split('\n')
        
        # Parse files (same logic but could be improved with better selectors)
        files = []
        # ... parsing logic ...
        
    chrome.close()
    return files


# Example 2: Using chrome-devtools-protocol (CDP) library
import cdp
from cdp import page, runtime, dom

async def extract_with_cdp():
    async with cdp.Client("http://localhost:9222") as client:
        # Create a new tab
        target = await client.create_target("https://claude.ai/projects")
        
        # Get page and enable domains
        async with client.session(target) as session:
            await page.enable()
            await runtime.enable()
            
            # Wait for page load
            await page.load_event_fired()
            
            # Get document
            doc = await dom.get_document()
            
            # Query selector all - native CDP support
            nodes = await dom.query_selector_all(doc.node_id, 'a[href*="/project/"]')
            
            # Get HTML of each node
            for node_id in nodes:
                html = await dom.get_outer_html(node_id)
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                # ... extract data ...


# Example 3: Even better - using Playwright/Selenium with CDP
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def extract_with_playwright():
    with sync_playwright() as p:
        # Connect to existing Chrome with CDP
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        
        # Navigate
        page.goto("https://claude.ai/projects")
        
        # Wait for content
        page.wait_for_selector('a[href*="/project/"]')
        
        # Get all project elements at once
        projects = page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href*="/project/"]')).map(link => {
                const div = link.querySelector('div');
                if (!div) return null;
                
                const children = Array.from(div.children);
                return {
                    name: children[0]?.textContent?.trim(),
                    description: children[1]?.textContent?.trim(),
                    url: link.href,
                    outerHTML: link.outerHTML  // Get HTML for BeautifulSoup if needed
                };
            }).filter(Boolean)
        """)
        
        # Find DNI project
        dni = next((p for p in projects if p['name'] == 'DNI'), None)
        
        if dni:
            page.goto(dni['url'])
            
            # Better: Use Playwright's built-in waiting
            page.wait_for_selector('text=Project knowledge')
            
            # Get page content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Or use Playwright's powerful selectors
            file_elements = page.query_selector_all('text=/\\d+ lines/')
            
            files = []
            for elem in file_elements:
                # Get surrounding context
                parent = elem.query_selector('xpath=..')
                if parent:
                    text = parent.inner_text()
                    # Parse file info...
        
        browser.close()


# Benefits summary:
"""
1. BeautifulSoup Benefits:
   - Powerful CSS selectors: soup.select('a[href*="/project/"]')
   - Easy text extraction: element.get_text(strip=True)
   - Navigate DOM: element.parent, element.find_next_sibling()
   - Handle malformed HTML gracefully
   
2. PyChromeDevTools Benefits:
   - Cleaner API: chrome.Page.navigate() vs manual command sending
   - Automatic result unwrapping
   - Better error handling
   - Event subscriptions: chrome.Page.loadEventFired += callback
   
3. chrome-devtools-protocol Benefits:
   - Async/await support
   - Type hints and IDE support
   - Native CDP protocol mapping
   - Better connection management
   
4. Playwright/Selenium Benefits:
   - High-level API with CDP access
   - Built-in waiting strategies
   - Cross-browser support
   - Powerful selectors (CSS, XPath, text, etc.)
   - Network interception capabilities
"""