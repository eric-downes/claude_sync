#!/usr/bin/env python3
"""
Simple test script to print knowledge file titles from DNI project.
"""
import logging
import sys
from src.chrome.robust_client import RobustChromeClient
from src.extractors.projects import ProjectExtractor
from src.extractors.knowledge import ProjectKnowledgeExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to extract and print DNI knowledge file titles."""
    logger.info("Starting DNI Project Knowledge File Title Extraction")
    logger.info("=" * 60)
    
    try:
        # Create Chrome client
        with RobustChromeClient() as client:
            # Get available pages
            pages = client.get_pages()
            claude_page = None
            
            # Find Claude.ai page
            for page in pages:
                if 'claude.ai' in page.get('url', ''):
                    claude_page = page
                    break
            
            if not claude_page:
                logger.error("No Claude.ai page found. Please open Claude.ai in Chrome with debugging enabled")
                logger.error("Run: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
                return 1
            
            # Connect to the page
            logger.info(f"Found Claude page: {claude_page.get('title', 'Untitled')}")
            client.connect_to_page(claude_page)
            
            # Create extractors
            project_extractor = ProjectExtractor(client)
            knowledge_extractor = ProjectKnowledgeExtractor(client)
            
            # Extract all projects
            logger.info("Extracting projects...")
            projects = project_extractor.extract_projects()
            logger.info(f"Found {len(projects)} projects")
            
            # Find DNI project
            dni_project = None
            for project in projects:
                if 'DNI' in project.name or 'dni' in project.name.lower():
                    dni_project = project
                    logger.info(f"Found DNI project: {project.name} (ID: {project.id})")
                    break
            
            if not dni_project:
                logger.error("DNI project not found!")
                logger.info("Available projects:")
                for p in projects:
                    logger.info(f"  - {p.name}")
                return 1
            
            # Extract knowledge files from DNI project
            logger.info(f"\nExtracting knowledge files from '{dni_project.name}'...")
            knowledge_files = knowledge_extractor.extract_project_knowledge(dni_project)
            
            if not knowledge_files:
                logger.warning("No knowledge files found in DNI project")
                return 0
            
            # Print the titles
            logger.info(f"\nFound {len(knowledge_files)} knowledge files in DNI project:")
            logger.info("-" * 60)
            
            for i, file in enumerate(knowledge_files, 1):
                logger.info(f"{i}. {file.name}")
                if file.file_type:
                    logger.info(f"   Type: {file.file_type}")
                if file.size:
                    logger.info(f"   Size: {file.size} bytes")
            
            logger.info("-" * 60)
            logger.info("Extraction complete!")
            
            return 0
            
    except Exception as e:
        logger.error(f"Error during extraction: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())