#!/usr/bin/env python3
"""
Proof of concept script to test accessing Claude.ai project knowledge
Run this locally to verify our approach works
"""

import asyncio
import json
from playwright.async_api import async_playwright
import os
from pathlib import Path

async def test_claude_access():
    """Test if we can access Claude.ai and extract project files"""
    
    print("Starting Playwright browser...")
    
    async with async_playwright() as p:
        # Use existing Chrome profile to leverage logged-in session
        user_data_dir = Path.home() / "Library/Application Support/Google/Chrome"
        
        # Launch Chrome with existing profile
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,  # Show browser so you can see what's happening
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        try:
            print("Navigating to Claude.ai...")
            await page.goto('https://claude.ai/projects')
            
            # Wait for projects to load
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # Give it a moment to fully load
            
            # Check if we're logged in by looking for project elements
            projects_selector = '[data-testid*="project"], [class*="project-card"], [class*="ProjectCard"]'
            
            try:
                await page.wait_for_selector(projects_selector, timeout=5000)
                print("✓ Successfully logged in to Claude.ai")
            except:
                print("✗ Not logged in or projects not found")
                print("Current URL:", page.url)
                print("Page title:", await page.title())
                
                # Take screenshot for debugging
                await page.screenshot(path='claude_login_state.png')
                print("Screenshot saved as claude_login_state.png")
                return
            
            # Extract project information
            print("\nLooking for projects...")
            
            # Try multiple possible selectors for projects
            project_elements = await page.query_selector_all(projects_selector)
            
            if not project_elements:
                print("No projects found with initial selector, trying alternatives...")
                # Try to find any clickable elements that might be projects
                all_links = await page.query_selector_all('a[href*="/project/"], a[href*="/chat/"]')
                print(f"Found {len(all_links)} potential project links")
            
            print(f"Found {len(project_elements)} projects")
            
            # Click on first project if found
            if project_elements:
                print("\nClicking on first project...")
                await project_elements[0].click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                
                # Look for knowledge/file section
                print("\nLooking for project knowledge files...")
                
                # Possible selectors for knowledge files
                file_selectors = [
                    '[data-testid*="knowledge"]',
                    '[class*="knowledge"]',
                    '[class*="file-list"]',
                    '[class*="document"]',
                    'button:has-text("Knowledge")',
                    'div:has-text("Project knowledge")'
                ]
                
                for selector in file_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        print(f"Found {len(elements)} elements with selector: {selector}")
                        break
                
                # Try to extract any visible file information
                print("\nExtracting visible text that might be files...")
                
                # Get all text content to analyze structure
                text_content = await page.inner_text('body')
                lines = text_content.split('\n')
                
                # Look for patterns that might indicate files
                potential_files = []
                for i, line in enumerate(lines):
                    if any(ext in line.lower() for ext in ['.txt', '.md', '.py', '.js', '.json', '.csv']):
                        potential_files.append(line.strip())
                        # Get context around the file
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        print(f"\nFound potential file: {line.strip()}")
                        print("Context:")
                        for j in range(start, end):
                            print(f"  {lines[j]}")
                
                if not potential_files:
                    print("No obvious file extensions found in page text")
                    
                # Take screenshot of project page
                await page.screenshot(path='claude_project_page.png', full_page=True)
                print("\nScreenshot of project page saved as claude_project_page.png")
                
                # Try to intercept network requests to understand API
                print("\n\nMonitoring network requests...")
                
                # Set up request interception
                requests_log = []
                
                def log_request(request):
                    if 'claude.ai' in request.url and any(path in request.url for path in ['/api/', '/project', '/file', '/knowledge']):
                        requests_log.append({
                            'url': request.url,
                            'method': request.method,
                            'headers': dict(request.headers)
                        })
                
                page.on('request', log_request)
                
                # Try to trigger some API calls by interacting with the page
                print("Interacting with page to trigger API calls...")
                
                # Click around to trigger requests
                clickable_elements = await page.query_selector_all('button, [role="button"], [onclick]')
                for elem in clickable_elements[:3]:  # Click first 3 buttons
                    try:
                        await elem.click()
                        await asyncio.sleep(1)
                    except:
                        pass
                
                # Log captured requests
                if requests_log:
                    print("\nCaptured API requests:")
                    for req in requests_log:
                        print(f"\n{req['method']} {req['url']}")
                        if 'authorization' in req['headers']:
                            print("  Has Authorization header")
                else:
                    print("\nNo API requests captured")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            print("\nTest complete. Browser will remain open for 10 seconds...")
            await asyncio.sleep(10)
            await browser.close()

if __name__ == "__main__":
    print("Claude.ai Access Test")
    print("=" * 50)
    print("This script will:")
    print("1. Open Chrome with your existing profile")
    print("2. Navigate to Claude.ai")
    print("3. Try to find and access project files")
    print("4. Log any API calls observed")
    print("\nMake sure you're logged into Claude.ai in Chrome first!")
    print("=" * 50)
    
    input("\nPress Enter to continue...")
    
    asyncio.run(test_claude_access())