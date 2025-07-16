#!/usr/bin/env python3
"""
Test DNI knowledge file extraction with fixed project title parsing.
"""
import logging
import sys
from src.chrome.robust_client import RobustChromeClient
from src.extractors.projects import ProjectExtractor
from src.extractors.knowledge import ProjectKnowledgeExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Extract and display DNI project knowledge files."""
    logger.info("\nDNI Project Knowledge Files")
    logger.info("=" * 60)
    
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
                logger.error("❌ No Claude.ai page found")
                return 1
            
            logger.info("✓ Connected to Claude.ai")
            client.connect_to_page(claude_page)
            
            # Create extractors
            project_extractor = ProjectExtractor(client)
            knowledge_extractor = ProjectKnowledgeExtractor(client)
            
            # Extract projects
            logger.info("✓ Extracting projects...")
            projects = project_extractor.extract_projects()
            
            # Find DNI project
            dni_project = None
            for project in projects:
                if project.name == 'DNI' or 'dni' in project.name.lower():
                    dni_project = project
                    break
            
            if not dni_project:
                logger.error("❌ DNI project not found")
                logger.info("\nAvailable projects:")
                for p in projects[:10]:  # Show first 10
                    desc = f" - {p.description}" if p.description else ""
                    logger.info(f"  • {p.name}{desc}")
                return 1
            
            # Display project info
            logger.info(f"\n✓ Found project: {dni_project.name}")
            if dni_project.description:
                logger.info(f"  Description: {dni_project.description}")
            if dni_project.updated:
                logger.info(f"  {dni_project.updated}")
            
            # Extract knowledge files
            logger.info("\n✓ Extracting knowledge files...")
            try:
                knowledge_files = knowledge_extractor.extract_project_knowledge(dni_project)
                
                if knowledge_files:
                    logger.info(f"\n📁 Knowledge Files in '{dni_project.name}':")
                    logger.info("-" * 60)
                    
                    for i, file in enumerate(knowledge_files, 1):
                        info = f"{i}. {file.name}"
                        if file.file_type:
                            info += f" ({file.file_type})"
                        if file.size:
                            info += f" - {file.size} bytes"
                        logger.info(info)
                    
                    logger.info("-" * 60)
                    logger.info(f"Total: {len(knowledge_files)} files")
                else:
                    logger.warning("⚠️  No knowledge files found")
                    
                    # Try manual extraction as fallback
                    logger.info("\nAttempting manual extraction...")
                    manual_files = client.evaluate_expression("""
                        JSON.stringify((() => {
                            const results = [];
                            const pageText = document.body.innerText;
                            
                            // Known file patterns
                            const filePatterns = [
                                { pattern: /Invoice valuation.*?(\\d+)\\s+lines/i, name: 'Invoice valuation' },
                                { pattern: /Illiquid pricing.*?(\\d+)\\s+lines/i, name: 'Illiquid pricing' },
                                { pattern: /legal memo.*?(\\d+)\\s+lines/i, name: 'legal memo' },
                                { pattern: /uk domestic.*?(\\d+)\\s+lines/i, name: 'uk domestic' },
                                { pattern: /traxpay podcast.*?(\\d+)\\s+lines/i, name: 'traxpay podcast BoE transcript' },
                                { pattern: /germany trade.*?(\\d+)\\s+lines/i, name: 'germany trade fi specific' }
                            ];
                            
                            filePatterns.forEach(({pattern, name}) => {
                                const match = pageText.match(pattern);
                                if (match) {
                                    results.push({
                                        name: name,
                                        lines: match[1],
                                        type: 'text'
                                    });
                                }
                            });
                            
                            return results;
                        })())
                    """)
                    
                    if manual_files:
                        logger.info(f"\n📁 Knowledge Files (manual extraction):")
                        logger.info("-" * 60)
                        for i, file in enumerate(manual_files, 1):
                            logger.info(f"{i}. {file['name']} ({file['lines']} lines) - {file['type']}")
                        logger.info("-" * 60)
                        logger.info(f"Total: {len(manual_files)} files")
                
            except Exception as e:
                logger.error(f"❌ Error extracting knowledge files: {e}")
                return 1
            
            return 0
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())