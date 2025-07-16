#!/usr/bin/env python3
"""
Refactored DNI extractor using BeautifulSoup with current ChromeClient.
This shows how even a minimal change (adding BeautifulSoup) greatly improves the code.
"""
from bs4 import BeautifulSoup
import time
from src.chrome.robust_client import RobustChromeClient


class ImprovedProjectExtractor:
    """Extract projects using BeautifulSoup for parsing."""
    
    def __init__(self, client: RobustChromeClient):
        self.client = client
    
    def get_page_html(self) -> str:
        """Get the full page HTML."""
        return self.client.evaluate_expression("document.documentElement.outerHTML")
    
    def extract_projects(self):
        """Extract all projects with clean parsing."""
        html = self.get_page_html()
        soup = BeautifulSoup(html, 'html.parser')
        
        projects = []
        # Find all project links
        for link in soup.select('a[href*="/project/"]'):
            href = link.get('href', '')
            project_id = href.split('/project/')[-1] if '/project/' in href else None
            
            # Parse the structure
            project = {
                'id': project_id,
                'url': f"https://claude.ai{href}" if href.startswith('/') else href
            }
            
            # Find the container div
            container = link.find('div')
            if container:
                divs = container.find_all('div', recursive=False)
                
                # First div is usually the title
                if len(divs) > 0:
                    project['name'] = divs[0].get_text(strip=True)
                
                # Second div is description (if not "Updated")
                if len(divs) > 1:
                    desc_text = divs[1].get_text(strip=True)
                    if 'Updated' not in desc_text:
                        project['description'] = desc_text
                
                # Find update time
                for div in divs:
                    text = div.get_text()
                    if 'Updated' in text and 'ago' in text:
                        project['updated'] = text.strip()
                        break
            else:
                # Fallback: just use link text
                project['name'] = link.get_text(strip=True).split('Updated')[0].strip()
            
            if project.get('name'):  # Only add if we found a name
                projects.append(project)
        
        return projects
    
    def extract_knowledge_files(self):
        """Extract knowledge files from project page."""
        html = self.get_page_html()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Get page text for parsing
        page_text = soup.get_text()
        
        # Find knowledge section
        if 'Project knowledge' not in page_text:
            return []
        
        # Extract text starting from "Project knowledge"
        knowledge_start = page_text.index('Project knowledge')
        knowledge_text = page_text[knowledge_start:]
        lines = knowledge_text.split('\n')
        
        files = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and UI elements
            if (not line or line in ['Project knowledge', 'Select file', 'Optional', 
                                     'Retrieving', 'Set project instructions'] or
                '%' in line or 'capacity' in line):
                i += 1
                continue
            
            # Check if next lines contain file info pattern
            if i + 2 < len(lines):
                next_line = lines[i + 1].strip()
                after_next = lines[i + 2].strip()
                
                # Pattern: filename / lines / type
                if next_line.endswith(' lines') and after_next in ['TEXT', 'PDF']:
                    try:
                        line_count = int(next_line.split()[0])
                        files.append({
                            'name': line,
                            'lines': line_count,
                            'type': after_next.lower()
                        })
                        i += 3
                        continue
                    except ValueError:
                        pass
            
            # Check for standalone PDF
            if i + 1 < len(lines) and lines[i + 1].strip() == 'PDF':
                files.append({
                    'name': line,
                    'type': 'pdf'
                })
                i += 2
                continue
            
            i += 1
        
        return files


def main():
    """Demo the improved extraction."""
    print("\nImproved DNI Knowledge File Extraction")
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
            
            # Create improved extractor
            extractor = ImprovedProjectExtractor(client)
            
            # Navigate to projects if needed
            current_url = client.evaluate_expression("window.location.href")
            if '/projects' not in current_url:
                print("✓ Navigating to projects page...")
                client.navigate_and_wait("https://claude.ai/projects")
            
            # Extract projects
            print("✓ Extracting projects with BeautifulSoup...")
            projects = extractor.extract_projects()
            
            print(f"✓ Found {len(projects)} projects")
            
            # Find DNI
            dni_project = next((p for p in projects if p['name'] == 'DNI'), None)
            
            if not dni_project:
                print("\n❌ DNI project not found")
                print("\nProjects found:")
                for p in projects[:5]:
                    print(f"  • {p['name']} - {p.get('description', 'No description')}")
                return 1
            
            print(f"\n✓ Found DNI project!")
            print(f"  Title: {dni_project['name']}")
            print(f"  Description: {dni_project.get('description', 'N/A')}")
            
            # Navigate to project
            print("\n✓ Opening DNI project...")
            client.navigate_and_wait(dni_project['url'])
            time.sleep(2)
            
            # Extract files
            print("✓ Extracting knowledge files...")
            files = extractor.extract_knowledge_files()
            
            if files:
                print(f"\n📁 Knowledge Files in '{dni_project['name']}':")
                print("-" * 60)
                
                for i, file in enumerate(files, 1):
                    info = f"{i}. {file['name']}"
                    if file.get('lines'):
                        info += f" ({file['lines']} lines)"
                    info += f" - {file['type']}"
                    print(info)
                
                print("-" * 60)
                print(f"Total: {len(files)} files")
                
                print("\n✅ Success! BeautifulSoup made the parsing much cleaner.")
            else:
                print("\n⚠️  No files found")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())