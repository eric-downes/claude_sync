"""
Project extractor for Claude.ai projects.
"""
import time
from typing import Any, Dict, List

from src.chrome.client import ChromeClient
from src.chrome.exceptions import (
    ChromeWebSocketError,
    ExtractionError,
    ProjectExtractionError,
)

from .models import Project


class ProjectExtractor:
    """Extracts project information from Claude.ai."""

    def __init__(self, client: ChromeClient):
        """
        Initialize project extractor.

        Args:
            client: Chrome client instance
        """
        self.client = client

    def navigate_to_projects_page(self) -> None:
        """Navigate to the projects page if not already there."""
        # Check current URL
        result = self.client.send_command(
            "Runtime.evaluate",
            {"expression": "window.location.href"}
        )
        current_url = result.get("result", {}).get("value", "")

        # Navigate if not on projects page
        if "/projects" not in current_url:
            self.client.send_command(
                "Page.navigate",
                {"url": "https://claude.ai/projects"}
            )
            time.sleep(3)  # Wait for navigation

    def _wait_for_projects_loaded(self, timeout: int = 30) -> None:
        """
        Wait for projects page to load.

        Args:
            timeout: Maximum seconds to wait

        Raises:
            ExtractionError: If timeout waiting for projects
        """
        check_script = """
        (() => {
            // Check if projects are loaded by looking for project elements
            // Modern Claude UI uses cards, not links
            const hasNewButton = Array.from(document.querySelectorAll('button')).some(btn =>
                btn.textContent.includes('New project') ||
                (btn.getAttribute('aria-label') || '').toLowerCase().includes('new project')
            );
            const isLoading = !!document.querySelector('[class*="loading"], [class*="spinner"], [class*="skeleton"]');

            // Look for project cards by checking for known project indicators
            const hasProjectCards = document.body.textContent.includes('Updated') &&
                                  document.body.textContent.includes('days ago');

            // Also check for the search box as an indicator the page is loaded
            const hasSearchBox = !!document.querySelector('input[placeholder*="Search projects"]');

            return (hasNewButton || hasProjectCards || hasSearchBox) && !isLoading;
        })()
        """

        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.client.send_command(
                "Runtime.evaluate",
                {"expression": check_script}
            )

            is_loaded = result.get("result", {}).get("value", False)
            if is_loaded:
                return

            time.sleep(0.5)

        raise ExtractionError(f"Timeout waiting for projects to load after {timeout}s")

    def _scroll_and_load_all(self) -> None:
        """
        Scroll through the page to load all projects.
        
        Claude.ai may use infinite scroll or lazy loading.
        """
        scroll_script = """
        (() => {
            const scrollable = document.querySelector('[style*="overflow"]') || 
                              document.querySelector('main') || 
                              document.body;
            return {
                scrollHeight: scrollable.scrollHeight,
                clientHeight: scrollable.clientHeight,
                needsScroll: scrollable.scrollHeight > scrollable.clientHeight,
                currentScroll: scrollable.scrollTop
            };
        })()
        """
        
        # Check if scrolling is needed
        result = self.client.send_command(
            "Runtime.evaluate",
            {"expression": scroll_script, "returnByValue": True}
        )
        
        scroll_info = result.get("result", {}).get("value", {})
        if not scroll_info.get("needsScroll", False):
            return
        
        # Scroll to load all projects
        previous_project_count = 0
        stable_count = 0
        max_scrolls = 10
        
        for i in range(max_scrolls):
            # Count current projects
            count_script = """
            Array.from(document.querySelectorAll('*'))
                .filter(el => el.textContent.match(/Updated \\d+ (day|week|month|year)s? ago/))
                .length
            """
            
            result = self.client.send_command(
                "Runtime.evaluate",
                {"expression": count_script, "returnByValue": True}
            )
            
            current_count = result.get("result", {}).get("value", 0)
            
            # If count hasn't changed, we might have loaded everything
            if current_count == previous_project_count:
                stable_count += 1
                if stable_count >= 2:
                    break
            else:
                stable_count = 0
            
            previous_project_count = current_count
            
            # Scroll down
            self.client.send_command(
                "Runtime.evaluate",
                {"expression": """
                    const scrollable = document.querySelector('[style*="overflow"]') || 
                                      document.querySelector('main') || 
                                      document.body;
                    scrollable.scrollTo(0, scrollable.scrollHeight);
                """}
            )
            
            # Wait for content to load
            time.sleep(1.5)
    
    def _extract_project_links(self) -> List[Dict[str, Any]]:
        """
        Extract project data using link-based detection.
        This is more reliable than text parsing.
        
        Returns:
            List of project dictionaries with href and basic info
        """
        link_script = """
        (() => {
            const links = Array.from(document.querySelectorAll('a[href*="/project/"]'));
            return links.map(link => {
                // Extract project ID from URL
                const projectId = link.href.split('/project/')[1] || null;
                
                // Initialize result
                const result = {
                    id: projectId,
                    url: link.href,
                    href: link.href
                };
                
                // Extract title and description from nested structure
                // The structure is typically:
                // <a><div><div>Title</div><div>Description</div><div>Updated...</div></div></a>
                
                const topDiv = link.querySelector('div');
                if (topDiv && topDiv.children.length >= 2) {
                    // First child div usually contains the title
                    const titleDiv = topDiv.children[0];
                    if (titleDiv) {
                        result.name = titleDiv.textContent.trim();
                    }
                    
                    // Second child div contains the description
                    const descDiv = topDiv.children[1];
                    if (descDiv && !descDiv.textContent.includes('Updated')) {
                        result.description = descDiv.textContent.trim();
                    }
                    
                    // Look for update time
                    for (let i = 0; i < topDiv.children.length; i++) {
                        const child = topDiv.children[i];
                        if (child.textContent.includes('Updated')) {
                            const updateMatch = child.textContent.match(/Updated (\\d+ (?:day|week|month|year)s? ago)/);
                            if (updateMatch) {
                                result.updated = updateMatch[0];
                            }
                            break;
                        }
                    }
                } else {
                    // Fallback: use the full link text and try to parse it
                    const linkText = link.textContent.trim();
                    const updateMatch = linkText.match(/Updated (\\d+ (?:day|week|month|year)s? ago)/);
                    
                    if (updateMatch) {
                        result.updated = updateMatch[0];
                        // Remove update info to get name
                        result.name = linkText.replace(updateMatch[0], '').trim();
                    } else {
                        result.name = linkText;
                    }
                }
                
                // Ensure we always have a name
                if (!result.name) {
                    result.name = link.textContent.trim().split('Updated')[0].trim();
                }
                
                return result;
            });
        })()
        """
        
        try:
            result = self.client.send_command(
                "Runtime.evaluate",
                {"expression": link_script, "returnByValue": True}
            )
            
            projects = result.get("result", {}).get("value", [])
            
            # Deduplicate by project ID
            unique_projects = {}
            for proj in projects:
                if proj.get('id'):
                    if proj['id'] not in unique_projects:
                        unique_projects[proj['id']] = proj
                    else:
                        # Keep the one with the better name
                        existing = unique_projects[proj['id']]
                        if len(proj['name']) < len(existing['name']):
                            unique_projects[proj['id']] = proj
            
            return list(unique_projects.values())
            
        except ChromeWebSocketError as e:
            raise ExtractionError(f"Failed to extract project links: {str(e)}") from e
    
    def _extract_project_data(self) -> List[Dict[str, Any]]:
        """
        Extract raw project data from the page.

        Returns:
            List of project dictionaries

        Raises:
            ExtractionError: If extraction fails
        """
        extract_script = """
        (() => {
            // Find all elements with update times
            const updateElements = Array.from(document.querySelectorAll('*'))
                .filter(el => el.textContent.match(/Updated \\d+ (day|week|month|year)s? ago/));
            
            // For each update element, find its project container
            const projectContainers = new Map();
            
            updateElements.forEach(updateEl => {
                // Walk up the DOM tree to find the project container
                let current = updateEl;
                let projectContainer = null;
                let projectName = '';
                
                // Go up until we find an element that contains more than just the update time
                while (current && current.parentElement) {
                    current = current.parentElement;
                    const text = current.textContent.trim();
                    
                    // Check if this element has substantial content beyond just the update time
                    if (text.length > 50 && text.includes('Updated')) {
                        // Extract potential project name (text before "Updated")
                        const beforeUpdate = text.split('Updated')[0].trim();
                        
                        // Skip if this looks like UI elements
                        if (beforeUpdate && 
                            !beforeUpdate.includes('Sort by') && 
                            !beforeUpdate.includes('Activity') &&
                            !beforeUpdate.includes('New project') &&
                            beforeUpdate.length > 3) {
                            projectContainer = current;
                            projectName = beforeUpdate;
                            break;
                        }
                    }
                }
                
                if (projectContainer && projectName) {
                    // Use the full text as a unique key
                    const key = projectContainer.textContent.trim();
                    if (!projectContainers.has(key)) {
                        projectContainers.set(key, {
                            element: projectContainer,
                            name: projectName,
                            updateElement: updateEl
                        });
                    }
                }
            });
            
            // Extract detailed info from each container
            const projects = [];
            projectContainers.forEach((info, key) => {
                const container = info.element;
                const text = container.textContent.trim();
                
                // Extract name more carefully
                let name = info.name;
                
                // Clean up the name - remove any trailing description that got included
                const lines = name.split(/\\n/).map(l => l.trim()).filter(l => l);
                if (lines.length > 0) {
                    // The first non-empty line is usually the project name
                    name = lines[0];
                }
                
                // Extract update time
                const updateMatch = text.match(/Updated (\\d+ (?:day|week|month|year)s? ago)/);
                const updated = updateMatch ? updateMatch[0] : null;
                
                // Extract description (text between name and update)
                let description = '';
                if (name && updated) {
                    const nameEnd = text.indexOf(name) + name.length;
                    const updateStart = text.indexOf(updated);
                    if (nameEnd > 0 && updateStart > nameEnd) {
                        description = text.substring(nameEnd, updateStart).trim();
                        // Clean up description - remove extra whitespace and newlines
                        description = description.replace(/\\s+/g, ' ').trim();
                    }
                }
                
                // Generate ID from name
                const id = 'proj-' + name.toLowerCase()
                    .replace(/[^a-z0-9]+/g, '-')
                    .replace(/^-|-$/g, '');
                
                projects.push({
                    name: name,
                    description: description || null,
                    updated: updated,
                    id: id,
                    url: 'https://claude.ai/project/' + id
                });
            });
            
            // Sort by update time (most recent first)
            projects.sort((a, b) => {
                const getUpdateValue = (updated) => {
                    if (!updated) return 0;
                    const match = updated.match(/(\\d+) (day|week|month|year)/);
                    if (!match) return 0;
                    const [_, num, unit] = match;
                    const multipliers = { day: 1, week: 7, month: 30, year: 365 };
                    return parseInt(num) * (multipliers[unit] || 1);
                };
                return getUpdateValue(a.updated) - getUpdateValue(b.updated);
            });
            
            return projects;
        })()
        """

        try:
            result = self.client.send_command(
                "Runtime.evaluate",
                {"expression": extract_script, "returnByValue": True}
            )

            # The script returns an array directly
            projects: List[Dict[str, Any]] = result.get("result", {}).get("value", [])
            return projects

        except ChromeWebSocketError as e:
            raise ExtractionError(f"Failed to extract project data: {str(e)}") from e

    def extract_projects(self, retry_count: int = 3) -> List[Project]:
        """
        Extract all projects from Claude.ai.

        Args:
            retry_count: Number of retries on failure

        Returns:
            List of Project objects

        Raises:
            ProjectExtractionError: If extraction fails after retries
        """
        for attempt in range(retry_count):
            try:
                # Navigate to projects page
                self.navigate_to_projects_page()

                # Wait for projects to load
                self._wait_for_projects_loaded()
                
                # Scroll to load all projects
                self._scroll_and_load_all()

                # Extract project data using both methods
                # Method 1: Link-based extraction (more reliable)
                link_projects = self._extract_project_links()
                
                # Method 2: Original update-based extraction
                update_projects = self._extract_project_data()
                
                # Combine results, preferring link-based data
                combined_projects = {}
                
                # Add all link-based projects
                for proj in link_projects:
                    if proj.get('id'):
                        combined_projects[proj['id']] = proj
                
                # Add update-based projects if they provide better data
                for proj in update_projects:
                    if proj.get('id'):
                        if proj['id'] in combined_projects:
                            # Update with better description if available
                            link_proj = combined_projects[proj['id']]
                            if not link_proj.get('description') and proj.get('description'):
                                link_proj['description'] = proj['description']
                        else:
                            combined_projects[proj['id']] = proj
                
                projects_data = list(combined_projects.values())

                # Convert to Project models
                projects = []
                for data in projects_data:
                    try:
                        # Skip if data is not a dictionary
                        if not isinstance(data, dict):
                            print(f"Warning: Skipping non-dict data: {data}")
                            continue

                        # Ensure we have required fields
                        if not data.get('id') or not data.get('name') or not data.get('url'):
                            print(f"Warning: Skipping project with missing required fields: {data}")
                            continue

                        project = Project(**data)
                        projects.append(project)
                    except Exception as e:
                        # Log but don't fail on individual project parsing
                        if isinstance(data, dict):
                            print(f"Warning: Failed to parse project {data.get('id', 'unknown')}: {e}")
                            print(f"  Data: {data}")
                        else:
                            print(f"Warning: Failed to parse non-dict data: {data}")

                return projects

            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(2)  # Wait before retry
                else:
                    raise ProjectExtractionError(
                        f"Failed to extract projects after {retry_count} attempts: {str(e)}"
                    ) from e

        return []  # Should never reach here
