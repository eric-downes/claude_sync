"""Knowledge file extractor for Claude.ai project pages."""
import re
import logging
from typing import List, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from claude_sync.models import KnowledgeFile

logger = logging.getLogger(__name__)


class KnowledgeExtractor:
    """Extract knowledge files from Claude.ai project pages."""
    
    def extract_from_html(self, html: str) -> List[KnowledgeFile]:
        """Extract knowledge files from HTML string.
        
        Args:
            html: Raw HTML content from project page
            
        Returns:
            List of KnowledgeFile objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        return self.extract_from_soup(soup)
    
    def extract_from_soup(self, soup: BeautifulSoup) -> List[KnowledgeFile]:
        """Extract knowledge files from BeautifulSoup object.
        
        Args:
            soup: Parsed BeautifulSoup object
            
        Returns:
            List of KnowledgeFile objects
        """
        files = []
        
        # Strategy 1: Look for thumbnail cards directly (most common)
        thumbnails = soup.find_all('div', {'data-testid': 'file-thumbnail'})
        if thumbnails:
            logger.debug(f"Found {len(thumbnails)} thumbnail cards")
            for thumb in thumbnails:
                file_data = self._parse_thumbnail_entry(thumb)
                if file_data:
                    files.append(file_data)
            return files
        
        # Strategy 2: Find knowledge section and look within it
        knowledge_header = None
        for h2 in soup.find_all('h2'):
            if 'Project knowledge' in h2.get_text():
                knowledge_header = h2
                break
        
        if not knowledge_header:
            logger.debug("No Project knowledge header found")
            return files
        
        # Find the parent container
        section = self._find_knowledge_container(knowledge_header)
        if not section:
            logger.debug("No knowledge container found")
            return files
        
        # Look for file entries within the section
        thumbnails = section.find_all('div', {'data-testid': 'file-thumbnail'})
        if thumbnails:
            for thumb in thumbnails:
                file_data = self._parse_thumbnail_entry(thumb)
                if file_data:
                    files.append(file_data)
        else:
            # Fallback to old structure with class="file-item"
            file_divs = section.find_all('div', class_='file-item')
            for div in file_divs:
                file_data = self._parse_file_entry(div)
                if file_data:
                    files.append(file_data)
        
        logger.info(f"Extracted {len(files)} knowledge files")
        return files
    
    def _find_knowledge_container(self, knowledge_header: Tag) -> Optional[Tag]:
        """Find the container that holds knowledge files."""
        # Look for a section first
        section = knowledge_header.find_parent('section')
        if section:
            return section
        
        # Look for parent div that contains the files
        parent = knowledge_header.parent
        while parent and parent.name != 'body':
            # Look for a container that has ul or file thumbnails
            if (parent.find('ul', class_=lambda c: c and 'grid' in ' '.join(c)) or 
                parent.find('div', {'data-testid': 'file-thumbnail'}) or
                parent.find('div', class_='file-item')):
                return parent
            parent = parent.parent
        
        # Fallback to immediate parent
        return knowledge_header.parent
    
    def _parse_thumbnail_entry(self, thumbnail_div: Tag) -> Optional[KnowledgeFile]:
        """Parse a thumbnail-style file entry (newer UI).
        
        The format is:
        <div data-testid="file-thumbnail">
          <button>
            <div>
              <h3>File name</h3>
              <p>XXX lines</p>
            </div>
            <div>
              <div>
                <p>text/pdf</p>
              </div>
            </div>
          </button>
        </div>
        
        Args:
            thumbnail_div: BeautifulSoup Tag for the thumbnail container
            
        Returns:
            KnowledgeFile object or None if not valid
        """
        try:
            # Find the h3 with the file name
            name_tag = thumbnail_div.find('h3')
            if not name_tag:
                return None
            
            name = name_tag.get_text(strip=True)
            if not name:
                return None
            
            # Find line count
            lines = None
            line_tags = thumbnail_div.find_all('p')
            for p in line_tags:
                text = p.get_text(strip=True)
                if 'lines' in text:
                    try:
                        lines = int(text.split()[0])
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Find file type
            file_type = None
            for p in line_tags:
                text = p.get_text(strip=True).lower()
                if text in ['text', 'pdf']:
                    file_type = text
                    break
            
            # If no explicit type found, default to text for files with lines
            if not file_type and lines:
                file_type = "text"
            elif not file_type:
                file_type = "unknown"
            
            return KnowledgeFile(
                name=name,
                file_type=file_type,
                lines=lines
            )
            
        except Exception:
            return None
    
    def _parse_file_entry(self, div: Tag) -> Optional[KnowledgeFile]:
        """Parse a single file entry div.
        
        The format we're looking for is:
        - File name as text
        - Optional line count (e.g., "489 lines")
        - File type (TEXT or PDF)
        - Button element
        
        Args:
            div: BeautifulSoup Tag for the file entry
            
        Returns:
            KnowledgeFile object or None if not a valid file entry
        """
        # Get all text nodes and child elements
        contents = list(div.children)
        if not contents:
            return None
        
        # Look for button - indicates this is a file entry
        has_button = div.find('button') is not None
        if not has_button:
            return None
        
        # Extract text content
        text_parts = []
        for item in contents:
            if isinstance(item, NavigableString):
                text = str(item).strip()
                if text:
                    # Split by newlines to handle multi-line text nodes
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    text_parts.extend(lines)
            elif isinstance(item, Tag) and item.name != 'button':
                text = item.get_text(strip=True)
                if text:
                    text_parts.append(text)
        
        if not text_parts:
            return None
        
        # Parse the text parts
        name = None
        file_type = None
        lines = None
        
        for i, part in enumerate(text_parts):
            # Check if this is a line count
            lines_match = re.match(r'^(\d+)\s+lines?$', part)
            if lines_match:
                lines = int(lines_match.group(1))
                continue
            
            # Check if this is a file type
            if part.upper() in ['TEXT', 'PDF']:
                file_type = part.lower()
                continue
            
            # Otherwise, it's likely the file name
            if name is None and part not in ['Select file', 'Optional', 'Retrieving']:
                name = part
        
        # Valid file entry must have name and type
        if not name or not file_type:
            return None
        
        return KnowledgeFile(
            name=name,
            file_type=file_type,
            lines=lines
        )