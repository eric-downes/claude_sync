"""Enhanced knowledge file extractor with better error handling."""
import re
from typing import List, Optional, Dict, Any
import logging

from bs4 import BeautifulSoup, Tag

from claude_sync.models import KnowledgeFile

logger = logging.getLogger(__name__)


class KnowledgeExtractorV2:
    """Enhanced extractor with multiple parsing strategies."""
    
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
        
        # Strategy 1: Modern thumbnail cards
        files.extend(self._extract_thumbnail_cards(soup))
        
        # Strategy 2: Legacy file-item divs (if any exist)
        if not files:
            files.extend(self._extract_legacy_file_items(soup))
        
        # Strategy 3: Fallback to any file-like structures
        if not files:
            files.extend(self._extract_fallback_patterns(soup))
        
        # Log extraction results
        logger.info(f"Extracted {len(files)} knowledge files")
        
        return files
    
    def _extract_thumbnail_cards(self, soup: BeautifulSoup) -> List[KnowledgeFile]:
        """Extract files from modern thumbnail card UI."""
        files = []
        
        # Find all thumbnail divs
        thumbnails = soup.find_all('div', {'data-testid': 'file-thumbnail'})
        logger.debug(f"Found {len(thumbnails)} thumbnail cards")
        
        for thumb in thumbnails:
            file_data = self._parse_thumbnail_entry(thumb)
            if file_data:
                files.append(file_data)
        
        return files
    
    def _extract_legacy_file_items(self, soup: BeautifulSoup) -> List[KnowledgeFile]:
        """Extract files from legacy file-item divs."""
        files = []
        
        # Find Project knowledge section first
        knowledge_section = self._find_knowledge_section(soup)
        if not knowledge_section:
            return files
        
        # Look for file-item divs
        file_divs = knowledge_section.find_all('div', class_='file-item')
        logger.debug(f"Found {len(file_divs)} legacy file items")
        
        for div in file_divs:
            file_data = self._parse_legacy_file_entry(div)
            if file_data:
                files.append(file_data)
        
        return files
    
    def _extract_fallback_patterns(self, soup: BeautifulSoup) -> List[KnowledgeFile]:
        """Fallback extraction for unknown patterns."""
        files = []
        
        # Look for any elements that might contain file information
        # This is a last resort when other methods fail
        
        # Pattern 1: Look for h3 tags with file-like names
        for h3 in soup.find_all('h3'):
            parent = h3.parent
            if parent and self._looks_like_file_container(parent):
                file_data = self._parse_generic_file_entry(parent)
                if file_data:
                    files.append(file_data)
        
        logger.debug(f"Fallback extraction found {len(files)} files")
        return files
    
    def _find_knowledge_section(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the Project knowledge section."""
        # Find the Project knowledge header
        for h2 in soup.find_all('h2'):
            if 'Project knowledge' in h2.get_text():
                # Look for the containing section
                parent = h2.parent
                while parent and parent.name != 'body':
                    # Check if this container has files
                    if (parent.find('div', {'data-testid': 'file-thumbnail'}) or
                        parent.find('div', class_='file-item') or
                        parent.find('ul', class_=lambda c: c and 'grid' in ' '.join(c))):
                        return parent
                    parent = parent.parent
                
                # If no better container found, use immediate parent
                return h2.parent
        
        return None
    
    def _parse_thumbnail_entry(self, thumbnail_div: Tag) -> Optional[KnowledgeFile]:
        """Parse a thumbnail-style file entry."""
        try:
            # Extract file name
            name = None
            h3 = thumbnail_div.find('h3')
            if h3:
                name = h3.get_text(strip=True)
            
            if not name:
                return None
            
            # Extract metadata
            file_info = {
                "name": name,
                "file_type": "unknown",
                "lines": None
            }
            
            # Look for line count and file type in p tags
            p_tags = thumbnail_div.find_all('p')
            for p in p_tags:
                text = p.get_text(strip=True)
                
                # Check for line count
                if 'lines' in text.lower():
                    match = re.search(r'(\d+)\s*lines?', text, re.I)
                    if match:
                        file_info["lines"] = int(match.group(1))
                
                # Check for file type
                elif text.lower() in ['text', 'pdf', 'csv', 'json']:
                    file_info["file_type"] = text.lower()
                elif 'text/pdf' in text.lower():
                    file_info["file_type"] = "pdf"
            
            # Check for PDF thumbnail image
            if thumbnail_div.find('img') and file_info["file_type"] == "unknown":
                file_info["file_type"] = "pdf"
            
            # Default to text if we have line count but no type
            if file_info["lines"] and file_info["file_type"] == "unknown":
                file_info["file_type"] = "text"
            
            return KnowledgeFile(**file_info)
            
        except Exception as e:
            logger.warning(f"Failed to parse thumbnail entry: {e}")
            return None
    
    def _parse_legacy_file_entry(self, div: Tag) -> Optional[KnowledgeFile]:
        """Parse a legacy file-item div."""
        try:
            # Similar to original implementation
            text_parts = []
            
            # Extract text content
            for child in div.children:
                if hasattr(child, 'get_text'):
                    text = child.get_text(strip=True)
                    if text and text not in ['Select file', 'Optional']:
                        text_parts.append(text)
                elif isinstance(child, str):
                    text = child.strip()
                    if text:
                        text_parts.append(text)
            
            # Parse the parts
            name = None
            file_type = "unknown"
            lines = None
            
            for part in text_parts:
                # Check line count
                if 'lines' in part.lower():
                    match = re.search(r'(\d+)\s*lines?', part, re.I)
                    if match:
                        lines = int(match.group(1))
                # Check file type
                elif part.upper() in ['TEXT', 'PDF', 'CSV', 'JSON']:
                    file_type = part.lower()
                # Otherwise it's likely the name
                elif not name:
                    name = part
            
            if name:
                return KnowledgeFile(
                    name=name,
                    file_type=file_type,
                    lines=lines
                )
            
        except Exception as e:
            logger.warning(f"Failed to parse legacy file entry: {e}")
        
        return None
    
    def _parse_generic_file_entry(self, container: Tag) -> Optional[KnowledgeFile]:
        """Parse a generic container that might have file info."""
        try:
            # Look for file-like patterns
            text_content = container.get_text(separator=' ', strip=True)
            
            # Skip if it's too short or looks like navigation
            if len(text_content) < 5 or 'knowledge' in text_content.lower():
                return None
            
            # Try to extract file info using regex
            name_match = re.search(r'^([^\\d]+?)(?:\s+\d+\s+lines)?', text_content)
            if name_match:
                name = name_match.group(1).strip()
                
                # Extract line count
                lines = None
                lines_match = re.search(r'(\d+)\s*lines?', text_content, re.I)
                if lines_match:
                    lines = int(lines_match.group(1))
                
                # Guess file type
                file_type = "text" if lines else "unknown"
                if '.pdf' in name.lower() or 'pdf' in text_content.lower():
                    file_type = "pdf"
                
                return KnowledgeFile(
                    name=name,
                    file_type=file_type,
                    lines=lines
                )
            
        except Exception as e:
            logger.warning(f"Failed to parse generic file entry: {e}")
        
        return None
    
    def _looks_like_file_container(self, element: Tag) -> bool:
        """Check if an element looks like it contains file information."""
        if not element:
            return False
        
        # Check for file-related classes or attributes
        classes = element.get('class', [])
        if any('file' in c or 'document' in c for c in classes):
            return True
        
        # Check for file-like content
        text = element.get_text(strip=True).lower()
        return any(indicator in text for indicator in ['lines', '.pdf', '.txt', '.csv'])
    
    def get_extraction_stats(self, html: str) -> Dict[str, Any]:
        """Get detailed statistics about the extraction process."""
        soup = BeautifulSoup(html, 'html.parser')
        
        stats = {
            "has_knowledge_header": False,
            "has_empty_message": "No knowledge added yet" in html,
            "thumbnail_count": len(soup.find_all('div', {'data-testid': 'file-thumbnail'})),
            "legacy_file_count": len(soup.find_all('div', class_='file-item')),
            "has_capacity_indicator": bool(soup.find(string=re.compile(r'\d+% of project capacity used'))),
            "total_files_extracted": len(self.extract_from_soup(soup))
        }
        
        # Check for knowledge header
        for h2 in soup.find_all('h2'):
            if 'Project knowledge' in h2.get_text():
                stats["has_knowledge_header"] = True
                break
        
        return stats