"""Project extractor for Claude.ai projects page."""
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from claude_sync.models import Project


class ProjectExtractor:
    """Extract projects from Claude.ai HTML pages."""
    
    def extract_from_html(self, html: str) -> List[Project]:
        """Extract projects from HTML string.
        
        Args:
            html: Raw HTML content from projects page
            
        Returns:
            List of Project objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        return self.extract_from_soup(soup)
    
    def extract_from_soup(self, soup: BeautifulSoup) -> List[Project]:
        """Extract projects from BeautifulSoup object.
        
        Args:
            soup: Parsed BeautifulSoup object
            
        Returns:
            List of Project objects
        """
        projects = []
        
        # Find all project links
        project_links = soup.find_all('a', href=lambda x: x and '/project/' in x)
        
        for link in project_links:
            project = self._parse_project_card(link)
            if project:
                projects.append(project)
        
        return projects
    
    def _parse_project_card(self, link: Tag) -> Optional[Project]:
        """Parse a single project card.
        
        Args:
            link: BeautifulSoup Tag for the project link
            
        Returns:
            Project object or None if parsing fails
        """
        # Extract project ID from URL
        href = link.get('href', '')
        if not href or '/project/' not in href:
            return None
        
        project_id = href.split('/project/')[-1]
        if not project_id:
            return None
        
        # Find divs inside the link
        divs = link.find_all('div', recursive=False)
        if not divs:
            return None
        
        # The first div inside the link contains the project info
        container_div = divs[0]
        inner_divs = container_div.find_all('div', recursive=False)
        
        if not inner_divs:
            return None
        
        # Extract name (first div)
        name = inner_divs[0].get_text(strip=True)
        if not name:
            return None
        
        # Extract description (second div, if exists and not "Updated")
        description = None
        if len(inner_divs) > 1:
            second_div_text = inner_divs[1].get_text(strip=True)
            # Check if this is the description or the update info
            if not any(keyword in second_div_text for keyword in ['Updated', 'ago']):
                description = second_div_text
        
        # Build full URL
        url = f"https://claude.ai{href}" if href.startswith('/') else href
        
        return Project(
            id=project_id,
            name=name,
            url=url,
            description=description
        )