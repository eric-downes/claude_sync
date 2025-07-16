#!/usr/bin/env python3
"""
Use the existing extractors to get DNI knowledge files.
"""
import logging
import sys
import time
from src.chrome.robust_client import RobustChromeClient
from src.extractors.projects import ProjectExtractor
from src.extractors.knowledge import ProjectKnowledgeExtractor

# Configure logging - suppress detailed logs
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Enable INFO for our script only


def main():
    """Extract DNI knowledge files using existing extractors."""
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
            
            # Create extractors
            project_extractor = ProjectExtractor(client)
            knowledge_extractor = ProjectKnowledgeExtractor(client)
            
            # First navigate to projects page to ensure we're in the right place
            print("✓ Navigating to projects page...")
            client.navigate_and_wait("https://claude.ai/projects")
            time.sleep(2)
            
            # Extract projects using the simpler link-based method
            print("✓ Extracting projects...")
            projects_data = project_extractor._extract_project_links()
            
            # Find DNI project
            dni_project = None
            for proj_data in projects_data:
                if 'dni' in proj_data.get('name', '').lower():
                    dni_project = proj_data
                    break
            
            if not dni_project:
                print("❌ DNI project not found")
                print("\nAvailable projects:")
                for p in projects_data[:10]:  # Show first 10
                    print(f"  - {p.get('name', 'Unknown')}")
                return 1
            
            print(f"✓ Found project: {dni_project['name']}")
            
            # Navigate to the project
            print("✓ Opening project...")
            client.navigate_and_wait(dni_project['url'])
            time.sleep(3)
            
            # Try to extract knowledge files using the knowledge extractor
            print("✓ Looking for knowledge files...")
            
            # Use the internal method directly for more control
            file_list = knowledge_extractor._extract_knowledge_files()
            
            if not file_list:
                print("\n⚠️  No knowledge files detected by automated extraction.")
                print("\nAttempting manual extraction...")
                
                # Try a more targeted extraction
                file_info = client.evaluate_expression("""
                    JSON.stringify((() => {
                        const results = [];
                        const pageText = document.body.innerText;
                        
                        // Known files from the page content
                        const patterns = [
                            /Invoice valuation.*?(\\d+)\\s+lines/i,
                            /Illiquid pricing.*?(\\d+)\\s+lines/i,
                            /legal memo.*?(\\d+)\\s+lines/i,
                            /uk domestic.*?(\\d+)\\s+lines/i,
                            /traxpay podcast.*?(\\d+)\\s+lines/i,
                            /germany trade.*?(\\d+)\\s+lines/i
                        ];
                        
                        const fileNames = [
                            'Invoice valuation',
                            'Illiquid pricing',
                            'legal memo',
                            'uk domestic',
                            'traxpay podcast BoE transcript',
                            'germany trade fi specific'
                        ];
                        
                        patterns.forEach((pattern, index) => {
                            const match = pageText.match(pattern);
                            if (match) {
                                results.push({
                                    name: fileNames[index],
                                    lines: match[1],
                                    type: 'text'
                                });
                            }
                        });
                        
                        // Check for PDF
                        if (pageText.includes('pdf')) {
                            results.push({
                                name: 'Unknown PDF file',
                                type: 'pdf'
                            });
                        }
                        
                        return results;
                    })())
                """)
                
                if file_info:
                    print(f"\n📁 Knowledge Files in '{dni_project['name']}':")
                    print("-" * 60)
                    for i, file in enumerate(file_info, 1):
                        info = f"{i}. {file['name']}"
                        if file.get('lines'):
                            info += f" ({file['lines']} lines)"
                        info += f" - {file['type']}"
                        print(info)
                    print("-" * 60)
                    print(f"Total: {len(file_info)} files")
                else:
                    print("Unable to extract file information")
            else:
                # Success with automated extraction
                print(f"\n📁 Knowledge Files in '{dni_project['name']}':")
                print("-" * 60)
                for i, file in enumerate(file_list, 1):
                    print(f"{i}. {file['name']} - {file['type']}")
                print("-" * 60)
                print(f"Total: {len(file_list)} files")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())