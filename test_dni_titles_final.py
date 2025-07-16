#!/usr/bin/env python3
"""
FINAL WORKING VERSION: Extract DNI project knowledge file titles.
"""
import time
from src.chrome.robust_client import RobustChromeClient


def extract_projects(client):
    """Extract projects with proper title/description separation."""
    result = client.send_command(
        "Runtime.evaluate",
        {
            "expression": """(() => {
                const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
                return links.map(link => {
                    const projectId = link.href.split('/project/')[1] || null;
                    const result = { id: projectId, url: link.href };
                    
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
                                if (match) result.updated = match[0];
                                break;
                            }
                        }
                    }
                    return result;
                });
            })()""",
            "returnByValue": True
        }
    )
    return result.get('result', {}).get('result', {}).get('value', [])


def extract_knowledge_files(client):
    """Extract knowledge files based on the observed format."""
    result = client.send_command(
        "Runtime.evaluate",
        {
            "expression": """(() => {
                const results = [];
                const pageText = document.body.innerText;
                
                // Find the Project knowledge section
                const knowledgeStart = pageText.indexOf('Project knowledge');
                if (knowledgeStart === -1) return results;
                
                // Get text after "Project knowledge"
                const knowledgeSection = pageText.substring(knowledgeStart);
                const lines = knowledgeSection.split('\\n').map(l => l.trim());
                
                // Parse the structure: filename, line count, type
                for (let i = 0; i < lines.length - 2; i++) {
                    const line = lines[i];
                    const nextLine = lines[i + 1];
                    const nextNextLine = lines[i + 2];
                    
                    // Check if next line has "X lines" pattern
                    if (nextLine && nextLine.match(/^\\d+\\s+lines$/)) {
                        const lineCount = parseInt(nextLine.match(/\\d+/)[0]);
                        
                        // Check if line after that is "TEXT" or "PDF"
                        if (nextNextLine && (nextNextLine === 'TEXT' || nextNextLine === 'PDF')) {
                            // Current line is the filename
                            if (line && !line.includes('Select file') && !line.includes('%') && 
                                !line.includes('Optional') && !line.includes('capacity')) {
                                results.push({
                                    name: line,
                                    lines: lineCount,
                                    type: nextNextLine.toLowerCase()
                                });
                                i += 2; // Skip the next two lines
                            }
                        }
                    } else if (line === 'PDF' && i > 0) {
                        // Standalone PDF entry - filename is on previous line
                        const prevLine = lines[i - 1];
                        if (prevLine && !prevLine.includes('Select file') && !prevLine.match(/\\d+\\s+lines/)) {
                            results.push({
                                name: prevLine,
                                type: 'pdf'
                            });
                        }
                    }
                }
                
                return results;
            })()""",
            "returnByValue": True
        }
    )
    return result.get('result', {}).get('result', {}).get('value', [])


def main():
    print("\nDNI Project Knowledge File Titles")
    print("=" * 60)
    
    try:
        with RobustChromeClient() as client:
            # Connect to Chrome
            pages = client.get_pages()
            claude_page = next((p for p in pages if 'claude.ai' in p.get('url', '')), None)
            
            if not claude_page:
                print("❌ No Claude.ai page found")
                return 1
            
            print("✓ Connected to Claude.ai")
            client.connect_to_page(claude_page)
            
            # Navigate to projects if needed
            current_url = client.evaluate_expression("window.location.href")
            if '/projects' not in current_url:
                print("✓ Navigating to projects page...")
                client.navigate_and_wait("https://claude.ai/projects")
            
            # Extract projects
            print("✓ Extracting projects...")
            projects = extract_projects(client)
            
            # Find DNI project
            dni_project = next((p for p in projects if p.get('name') == 'DNI'), None)
            
            if not dni_project:
                print("❌ DNI project not found")
                return 1
            
            print(f"\n✓ Found DNI project!")
            print(f"  Title: {dni_project['name']}")
            print(f"  Description: {dni_project.get('description', 'N/A')}")
            
            # Navigate to DNI project
            print("\n✓ Opening DNI project...")
            client.navigate_and_wait(dni_project['url'])
            time.sleep(2)
            
            # Extract knowledge files
            print("✓ Extracting knowledge files...")
            files = extract_knowledge_files(client)
            
            if files:
                print(f"\n📁 Knowledge Files in '{dni_project['name']}':")
                print("-" * 60)
                
                for i, file in enumerate(files, 1):
                    if file.get('lines'):
                        print(f"{i}. {file['name']} ({file['lines']} lines) - {file['type']}")
                    else:
                        print(f"{i}. {file['name']} - {file['type']}")
                
                print("-" * 60)
                print(f"Total: {len(files)} files")
            else:
                print("\n⚠️  No knowledge files found")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())