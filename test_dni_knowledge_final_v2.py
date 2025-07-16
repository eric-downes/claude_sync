#!/usr/bin/env python3
"""
Final version to extract DNI project knowledge file titles.
"""
import json
import time
from src.chrome.robust_client import RobustChromeClient

def extract_projects_properly(client):
    """Extract projects with separated titles and descriptions."""
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
                    
                    const topDiv = link.querySelector('div');
                    if (topDiv && topDiv.children.length >= 2) {
                        result.name = topDiv.children[0].textContent.trim();
                        
                        const descDiv = topDiv.children[1];
                        if (descDiv && !descDiv.textContent.includes('Updated')) {
                            result.description = descDiv.textContent.trim();
                        }
                        
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
                        result.name = link.textContent.trim().split('Updated')[0].trim();
                    }
                    
                    return result;
                });
            })()""",
            "returnByValue": True
        }
    )
    
    if 'result' in result and 'result' in result['result'] and 'value' in result['result']['result']:
        return result['result']['result']['value']
    return []


def extract_knowledge_files_comprehensive(client):
    """More comprehensive knowledge file extraction."""
    # First, check if we're on the right page
    page_check = client.send_command(
        "Runtime.evaluate",
        {
            "expression": "document.body.innerText.includes('Project knowledge')",
            "returnByValue": True
        }
    )
    
    is_on_project = page_check.get('result', {}).get('result', {}).get('value', False)
    if not is_on_project:
        print("  ⚠️  Not on project page or knowledge section not found")
        return []
    
    # Extract files with a more targeted approach
    result = client.send_command(
        "Runtime.evaluate",
        {
            "expression": """(() => {
                const results = [];
                const pageText = document.body.innerText;
                
                // Split by lines and process
                const lines = pageText.split('\\n');
                
                // State machine to parse file entries
                let currentFile = null;
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    
                    // Skip empty lines and UI elements
                    if (!line || line.includes('Select file') || line.includes('Project knowledge') || 
                        line.includes('Optional') || line.includes('capacity')) {
                        continue;
                    }
                    
                    // Check if this line contains "X lines"
                    const linesMatch = line.match(/(\\d+)\\s+lines/);
                    
                    if (linesMatch) {
                        // This line has line count, check if it's part of a file entry
                        const lineCount = parseInt(linesMatch[1]);
                        
                        // Check if "text" follows on same line
                        if (line.includes('text')) {
                            // Pattern: "filename X lines text"
                            const beforeLines = line.substring(0, line.indexOf(linesMatch[0])).trim();
                            if (beforeLines && !beforeLines.includes('%') && !beforeLines.includes('Updated')) {
                                results.push({
                                    name: beforeLines,
                                    lines: lineCount,
                                    type: 'text'
                                });
                            }
                        } else if (i > 0) {
                            // Check if previous line might be filename
                            const prevLine = lines[i-1].trim();
                            if (prevLine && !prevLine.includes('lines') && !prevLine.includes('Select') && 
                                !prevLine.includes('%') && prevLine.length < 100) {
                                results.push({
                                    name: prevLine,
                                    lines: lineCount,
                                    type: 'text'
                                });
                            }
                        }
                    } else if (line.toLowerCase() === 'pdf' && i > 0) {
                        // PDF file - filename is likely on previous line
                        const prevLine = lines[i-1].trim();
                        if (prevLine && !prevLine.includes('lines') && !prevLine.includes('Select')) {
                            results.push({
                                name: prevLine,
                                type: 'pdf'
                            });
                        }
                    }
                }
                
                // If no files found with above method, try known patterns
                if (results.length === 0) {
                    const knownFiles = [
                        'Invoice valuation',
                        'Illiquid pricing', 
                        'legal memo',
                        'uk domestic',
                        'traxpay podcast BoE transcript',
                        'germany trade fi specific'
                    ];
                    
                    knownFiles.forEach(fileName => {
                        if (pageText.includes(fileName)) {
                            const pattern = new RegExp(fileName + '.*?(\\\\d+)\\\\s+lines', 'i');
                            const match = pageText.match(pattern);
                            if (match) {
                                results.push({
                                    name: fileName,
                                    lines: parseInt(match[1]),
                                    type: 'text'
                                });
                            }
                        }
                    });
                }
                
                // Deduplicate
                const unique = new Map();
                results.forEach(file => {
                    const key = file.name.toLowerCase().replace(/\\s+/g, '');
                    if (!unique.has(key)) {
                        unique.set(key, file);
                    }
                });
                
                return Array.from(unique.values());
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
            
            current_url = client.evaluate_expression("window.location.href")
            if '/projects' not in current_url:
                print("✓ Navigating to projects page...")
                client.navigate_and_wait("https://claude.ai/projects")
            
            print("✓ Extracting projects...")
            projects = extract_projects_properly(client)
            
            if not projects:
                print("❌ No projects found")
                return 1
            
            dni_project = None
            for proj in projects:
                if proj.get('name') == 'DNI':
                    dni_project = proj
                    break
            
            if not dni_project:
                print("❌ DNI project not found")
                return 1
            
            print(f"\n✓ Found DNI project!")
            print(f"  Title: {dni_project['name']}")
            if dni_project.get('description'):
                print(f"  Description: {dni_project['description']}")
            if dni_project.get('updated'):
                print(f"  {dni_project['updated']}")
            
            print("\n✓ Opening DNI project...")
            client.navigate_and_wait(dni_project['url'])
            time.sleep(2)  # Extra wait for content
            
            print("✓ Extracting knowledge files...")
            knowledge_files = extract_knowledge_files_comprehensive(client)
            
            if knowledge_files:
                print(f"\n📁 Knowledge Files in '{dni_project['name']}':")
                print("-" * 60)
                
                # Sort by name for consistent output
                knowledge_files.sort(key=lambda x: x['name'])
                
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
                
                # Debug: show page snippet
                snippet = client.evaluate_expression(
                    "document.body.innerText.substring(document.body.innerText.indexOf('Project knowledge'), document.body.innerText.indexOf('Project knowledge') + 500)"
                )
                if snippet:
                    print(f"\nDebug - Page content near 'Project knowledge':")
                    print(snippet)
            
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()