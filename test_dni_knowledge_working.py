#!/usr/bin/env python3
"""
Working test to extract DNI project knowledge file titles.
"""
import json
from src.chrome.robust_client import RobustChromeClient

def extract_projects_with_proper_titles(client):
    """Extract projects with properly separated titles and descriptions."""
    # Use send_command directly with returnByValue
    result = client.send_command(
        "Runtime.evaluate",
        {
            "expression": """(() => {
                const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
                return links.map(link => {
                    const projectId = link.href.split('/project/')[1] || null;
                    
                    const result = {
                        id: projectId,
                        url: link.href
                    };
                    
                    // Extract title and description from nested divs
                    const topDiv = link.querySelector('div');
                    if (topDiv && topDiv.children.length >= 2) {
                        // First child = title
                        const titleDiv = topDiv.children[0];
                        if (titleDiv) {
                            result.name = titleDiv.textContent.trim();
                        }
                        
                        // Second child = description (if not "Updated")
                        const descDiv = topDiv.children[1];
                        if (descDiv && !descDiv.textContent.includes('Updated')) {
                            result.description = descDiv.textContent.trim();
                        }
                        
                        // Find update time
                        for (let child of topDiv.children) {
                            if (child.textContent.includes('Updated')) {
                                const match = child.textContent.match(/Updated (\\d+ (?:day|week|month|year)s? ago)/);
                                if (match) {
                                    result.updated = match[0];
                                }
                                break;
                            }
                        }
                    } else {
                        // Fallback
                        result.name = link.textContent.trim().split('Updated')[0].trim();
                    }
                    
                    return result;
                });
            })()""",
            "returnByValue": True
        }
    )
    
    # Extract the value from the result
    if 'result' in result and 'result' in result['result'] and 'value' in result['result']['result']:
        return result['result']['result']['value']
    return []


def extract_knowledge_files(client):
    """Extract knowledge file information from current project page."""
    result = client.send_command(
        "Runtime.evaluate",
        {
            "expression": """(() => {
                const results = [];
                const pageText = document.body.innerText;
                
                // Known file patterns based on what we've seen
                const fileInfo = [
                    { pattern: /Invoice valuation.*?(\\d+)\\s+lines/i, name: 'Invoice valuation' },
                    { pattern: /Illiquid pricing.*?(\\d+)\\s+lines/i, name: 'Illiquid pricing' },
                    { pattern: /legal memo.*?(\\d+)\\s+lines/i, name: 'legal memo' },
                    { pattern: /uk domestic.*?(\\d+)\\s+lines/i, name: 'uk domestic' },
                    { pattern: /traxpay podcast.*?(\\d+)\\s+lines/i, name: 'traxpay podcast BoE transcript' },
                    { pattern: /germany trade.*?(\\d+)\\s+lines/i, name: 'germany trade fi specific' }
                ];
                
                fileInfo.forEach(({pattern, name}) => {
                    const match = pageText.match(pattern);
                    if (match) {
                        results.push({
                            name: name,
                            lines: parseInt(match[1]),
                            type: 'text'
                        });
                    }
                });
                
                // Check for PDF files
                if (pageText.toLowerCase().includes('pdf')) {
                    // Try to find PDF filename
                    const pdfMatch = pageText.match(/([^\\n]+?)\\s*pdf/i);
                    if (pdfMatch) {
                        const possibleName = pdfMatch[1].trim().split(/\\s+/).slice(-3).join(' ');
                        results.push({
                            name: possibleName || 'Document',
                            type: 'pdf'
                        });
                    }
                }
                
                return results;
            })()""",
            "returnByValue": True
        }
    )
    
    if 'result' in result and 'result' in result['result'] and 'value' in result['result']['result']:
        return result['result']['result']['value']
    return []


def main():
    print("\nDNI Project Knowledge Files")
    print("=" * 60)
    
    try:
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
            
            # Check if we need to navigate to projects
            current_url = client.evaluate_expression("window.location.href")
            if '/projects' not in current_url:
                print("✓ Navigating to projects page...")
                client.navigate_and_wait("https://claude.ai/projects")
            
            # Extract projects with fixed title parsing
            print("✓ Extracting projects...")
            projects = extract_projects_with_proper_titles(client)
            
            if not projects:
                print("❌ No projects found")
                return 1
            
            print(f"✓ Found {len(projects)} projects")
            
            # Find DNI project
            dni_project = None
            for proj in projects:
                if proj.get('name') == 'DNI':
                    dni_project = proj
                    break
            
            if not dni_project:
                print("\n❌ DNI project not found")
                print("\nAvailable projects:")
                for p in projects[:10]:
                    desc = f" - {p.get('description', '')}" if p.get('description') else ""
                    print(f"  • {p.get('name', 'Unknown')}{desc}")
                return 1
            
            # Display DNI project info
            print(f"\n✓ Found DNI project!")
            print(f"  Title: {dni_project['name']}")
            if dni_project.get('description'):
                print(f"  Description: {dni_project['description']}")
            if dni_project.get('updated'):
                print(f"  {dni_project['updated']}")
            
            # Navigate to DNI project
            print("\n✓ Opening DNI project...")
            client.navigate_and_wait(dni_project['url'])
            
            # Extract knowledge files
            print("✓ Extracting knowledge files...")
            knowledge_files = extract_knowledge_files(client)
            
            if knowledge_files:
                print(f"\n📁 Knowledge Files in '{dni_project['name']}':")
                print("-" * 60)
                
                for i, file in enumerate(knowledge_files, 1):
                    info = f"{i}. {file['name']}"
                    if file.get('lines'):
                        info += f" ({file['lines']} lines)"
                    info += f" - {file['type']}"
                    print(info)
                
                print("-" * 60)
                print(f"Total: {len(knowledge_files)} files")
            else:
                print("\n⚠️  No knowledge files found")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()