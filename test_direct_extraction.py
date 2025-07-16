#!/usr/bin/env python3
"""Test direct extraction with the fixed extractor."""
from src.chrome.robust_client import RobustChromeClient

def main():
    print("\nDirect Project Extraction Test")
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
        
        print("✓ Connected to Claude.ai")
        client.connect_to_page(claude_page)
        
        # Run the exact extraction script from the fixed extractor
        print("✓ Running extraction script...")
        
        result = client.send_command(
            "Runtime.evaluate",
            {"expression": """(() => {
            const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
            return links.map(link => {
                // Extract project ID from URL
                const projectId = link.href.split('/project/')[1] || null;
                
                // Initialize result
                const result = {
                    id: projectId,
                    url: link.href,
                    href: link.href
                };
                
                // Extract title and description from nested structure
                // The structure is typically:
                // <a><div><div>Title</div><div>Description</div><div>Updated...</div></div></a>
                
                const topDiv = link.querySelector('div');
                if (topDiv && topDiv.children.length >= 2) {
                    // First child div usually contains the title
                    const titleDiv = topDiv.children[0];
                    if (titleDiv) {
                        result.name = titleDiv.textContent.trim();
                    }
                    
                    // Second child div contains the description
                    const descDiv = topDiv.children[1];
                    if (descDiv && !descDiv.textContent.includes('Updated')) {
                        result.description = descDiv.textContent.trim();
                    }
                    
                    // Look for update time
                    for (let i = 0; i < topDiv.children.length; i++) {
                        const child = topDiv.children[i];
                        if (child.textContent.includes('Updated')) {
                            const updateMatch = child.textContent.match(/Updated (\\d+ (?:day|week|month|year)s? ago)/);
                            if (updateMatch) {
                                result.updated = updateMatch[0];
                            }
                            break;
                        }
                    }
                } else {
                    // Fallback: use the full link text and try to parse it
                    const linkText = link.textContent.trim();
                    const updateMatch = linkText.match(/Updated (\\d+ (?:day|week|month|year)s? ago)/);
                    
                    if (updateMatch) {
                        result.updated = updateMatch[0];
                        // Remove update info to get name
                        result.name = linkText.replace(updateMatch[0], '').trim();
                    } else {
                        result.name = linkText;
                    }
                }
                
                // Ensure we always have a name
                if (!result.name) {
                    result.name = link.textContent.trim().split('Updated')[0].trim();
                }
                
                return result;
            });
        })()""", "returnByValue": True}
        )
        
        # Check raw result
        print(f"\nRaw result type: {type(result)}")
        print(f"Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        
        if 'result' in result:
            print(f"Result.result keys: {result['result'].keys()}")
            if 'value' in result['result']:
                projects = result['result']['value']
                print(f"Projects type: {type(projects)}")
                print(f"Projects count: {len(projects) if isinstance(projects, list) else 'N/A'}")
                
                # Show first few projects
                if isinstance(projects, list) and projects:
                    print("\n📋 Projects found:")
                    print("-" * 60)
                    
                    for i, proj in enumerate(projects[:5]):
                        print(f"\n{i+1}. {proj.get('name', 'Unknown')}")
                        if proj.get('description'):
                            print(f"   Description: {proj['description']}")
                        if proj.get('updated'):
                            print(f"   {proj['updated']}")
                        print(f"   ID: {proj.get('id', 'N/A')}")
                    
                    # Look for DNI
                    dni_projects = [p for p in projects if p.get('name') == 'DNI' or 'dni' in p.get('name', '').lower()]
                    if dni_projects:
                        print("\n✓ Found DNI project(s):")
                        for p in dni_projects:
                            print(f"  - {p.get('name')} ({p.get('description', 'No description')})")
    
    return 0

if __name__ == "__main__":
    main()