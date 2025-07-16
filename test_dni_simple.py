#!/usr/bin/env python3
"""
Simple direct test of DNI knowledge files with fixed title extraction.
"""
import sys
import time
from src.chrome.robust_client import RobustChromeClient
from src.extractors.projects import ProjectExtractor

def main():
    print("\nDNI Project Knowledge Files (Simple Test)")
    print("=" * 60)
    
    with RobustChromeClient() as client:
        # Connect to Chrome
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
        
        # Create project extractor
        project_extractor = ProjectExtractor(client)
        
        # Check if we're already on projects page
        current_url = client.evaluate_expression("window.location.href")
        if '/projects' not in current_url:
            print("✓ Navigating to projects page...")
            client.navigate_and_wait("https://claude.ai/projects")
            time.sleep(2)
        
        # Extract projects using the fixed link extractor directly
        print("✓ Extracting projects...")
        projects_data = project_extractor._extract_project_links()
        
        print(f"\n📋 Found {len(projects_data)} projects:")
        print("-" * 60)
        
        # Find and display DNI project
        dni_project = None
        for proj in projects_data:
            name = proj.get('name', '')
            desc = proj.get('description', '')
            
            # Display first few projects
            if len(projects_data) <= 10 or name == 'DNI' or 'dni' in name.lower():
                if desc:
                    print(f"• {name} - {desc}")
                else:
                    print(f"• {name}")
                
                if proj.get('updated'):
                    print(f"  {proj['updated']}")
                print()
            
            if name == 'DNI' or 'dni' in name.lower():
                dni_project = proj
        
        if not dni_project:
            print("❌ DNI project not found")
            return 1
        
        print("-" * 60)
        print(f"\n✓ Found DNI project!")
        print(f"  Title: {dni_project['name']}")
        if dni_project.get('description'):
            print(f"  Description: {dni_project['description']}")
        print(f"  URL: {dni_project['url']}")
        
        # Navigate to DNI project
        print("\n✓ Opening DNI project...")
        client.navigate_and_wait(dni_project['url'])
        time.sleep(3)
        
        # Extract knowledge files manually
        print("✓ Looking for knowledge files...")
        
        # Check page content
        page_text = client.evaluate_expression("document.body.innerText")
        
        # Extract file info
        file_info = client.evaluate_expression("""
            JSON.stringify((() => {
                const results = [];
                const pageText = document.body.innerText;
                
                // Look for lines that contain file information
                const lines = pageText.split('\\n');
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    
                    // Match patterns like "filename 123 lines text"
                    if (line.includes('lines') && line.includes('text')) {
                        // Try to extract components
                        const parts = line.split(/\\s+/);
                        const linesIndex = parts.indexOf('lines');
                        
                        if (linesIndex > 0 && parts[linesIndex - 1].match(/\\d+/)) {
                            const lineCount = parts[linesIndex - 1];
                            const fileName = parts.slice(0, linesIndex - 1).join(' ');
                            
                            if (fileName && !fileName.includes('Updated') && !fileName.includes('%')) {
                                results.push({
                                    name: fileName,
                                    lines: lineCount,
                                    type: 'text'
                                });
                            }
                        }
                    }
                }
                
                // Also try known patterns
                const knownPatterns = [
                    'Invoice valuation',
                    'Illiquid pricing',
                    'legal memo',
                    'uk domestic',
                    'traxpay podcast BoE transcript',
                    'germany trade fi specific'
                ];
                
                knownPatterns.forEach(pattern => {
                    const regex = new RegExp(pattern + '.*?(\\\\d+)\\\\s+lines', 'i');
                    const match = pageText.match(regex);
                    if (match && !results.find(r => r.name.toLowerCase().includes(pattern.toLowerCase()))) {
                        results.push({
                            name: pattern,
                            lines: match[1],
                            type: 'text'
                        });
                    }
                });
                
                return results;
            })())
        """)
        
        if file_info and file_info.length > 0:
            print(f"\n📁 Knowledge Files in '{dni_project['name']}':")
            print("-" * 60)
            
            for i, file in enumerate(file_info, 1):
                print(f"{i}. {file['name']} ({file['lines']} lines) - {file['type']}")
            
            print("-" * 60)
            print(f"Total: {len(file_info)} files")
        else:
            print("\n⚠️  No knowledge files found")
            
            # Show a snippet of page content for debugging
            snippet = page_text[:500] if page_text else "No content"
            print(f"\nPage snippet: {snippet}...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())