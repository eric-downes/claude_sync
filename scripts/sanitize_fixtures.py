#!/usr/bin/env python3
"""Sanitize raw HTML fixtures by replacing personal information."""
import re
import random
from pathlib import Path
from bs4 import BeautifulSoup


def generate_project_name(index):
    """Generate generic project name."""
    categories = ["Test", "Demo", "Sample", "Example", "Mock"]
    types = ["Project", "App", "System", "Tool", "Service"]
    return f"{random.choice(categories)} {random.choice(types)} {index}"


def generate_description(index):
    """Generate generic description."""
    descriptions = [
        "A sample project for testing purposes",
        "Demo application with example data",
        "Test project for development",
        "Example system for demonstration",
        "Mock service for integration testing",
        "Sample tool for educational purposes"
    ]
    return descriptions[index % len(descriptions)]


def generate_file_name(index):
    """Generate generic file name."""
    prefixes = ["document", "file", "data", "content", "example", "sample", "test"]
    extensions = ["txt", "pdf", "txt", "pdf", "txt"]  # More txt than pdf
    return f"{random.choice(prefixes)}_{index}.{random.choice(extensions)}"


def sanitize_project_id(match):
    """Replace project ID with generic one."""
    # Keep the format but use generic IDs
    return f"/project/{chr(97 + sanitize_project_id.counter)}" + "0" * 35
sanitize_project_id.counter = 0


def sanitize_projects_page(html):
    """Sanitize projects list page."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all project cards
    project_cards = soup.find_all('a', href=re.compile(r'/project/[a-f0-9-]+'))
    
    project_counter = 1
    for card in project_cards:
        # Update href
        original_href = card.get('href', '')
        new_id = f"project-{project_counter:03d}"
        card['href'] = f"/project/{new_id}"
        
        # Find and update project name
        name_elem = card.find('h3')
        if name_elem:
            name_elem.string = generate_project_name(project_counter)
        
        # Find and update description
        desc_elem = card.find('p')
        if desc_elem:
            desc_elem.string = generate_description(project_counter)
        
        project_counter += 1
    
    # Replace any remaining project IDs in the HTML
    html_str = str(soup)
    html_str = re.sub(r'/project/[a-f0-9-]{36}', lambda m: f"/project/project-{random.randint(1,100):03d}", html_str)
    
    return html_str


def sanitize_project_page(html):
    """Sanitize individual project page."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Update page title
    title = soup.find('title')
    if title:
        title.string = "Sample Project - Claude"
    
    # Update project name in header
    h1_tags = soup.find_all('h1')
    for h1 in h1_tags:
        if h1.get_text().strip():
            h1.string = "Sample Project"
    
    # Update knowledge files
    file_counter = 1
    
    # Handle thumbnail style files
    thumbnails = soup.find_all('div', {'data-testid': 'file-thumbnail'})
    for thumb in thumbnails:
        h3 = thumb.find('h3')
        if h3:
            h3.string = generate_file_name(file_counter)
        
        # Update line counts to generic values
        line_tags = thumb.find_all('p')
        for p in line_tags:
            text = p.get_text(strip=True)
            if 'lines' in text:
                p.string = f"{random.randint(50, 500)} lines"
        
        file_counter += 1
    
    # Handle old style file items
    file_items = soup.find_all('div', class_='file-item')
    for item in file_items:
        # Replace file names
        text_content = item.get_text()
        if text_content:
            # Replace with generic file name
            item.string = f"{generate_file_name(file_counter)} {random.randint(50, 500)} lines TEXT"
            file_counter += 1
    
    # Replace any email addresses
    html_str = str(soup)
    html_str = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', 'user@example.com', html_str)
    
    # Replace any remaining UUIDs
    html_str = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', 
                      lambda m: f"sample-id-{random.randint(1000, 9999)}", html_str)
    
    return html_str


def main():
    """Main sanitization process."""
    fixtures_dir = Path("tests/fixtures")
    fixtures_dir.mkdir(exist_ok=True)
    
    # Process projects page
    projects_file = fixtures_dir / "raw_projects_page.html"
    if projects_file.exists():
        print("Sanitizing projects page...")
        with open(projects_file, 'r') as f:
            html = f.read()
        
        sanitized = sanitize_projects_page(html)
        
        with open(fixtures_dir / "sanitized_projects_page.html", 'w') as f:
            f.write(sanitized)
        print("Created sanitized_projects_page.html")
    
    # Process project page
    project_file = fixtures_dir / "raw_project_page.html"
    if project_file.exists():
        print("Sanitizing project page...")
        with open(project_file, 'r') as f:
            html = f.read()
        
        sanitized = sanitize_project_page(html)
        
        with open(fixtures_dir / "sanitized_project_page.html", 'w') as f:
            f.write(sanitized)
        print("Created sanitized_project_page.html")
    
    # Create a minimal projects page for testing
    minimal_projects = """
    <html>
    <body>
        <h1>Projects</h1>
        <div>
            <a href="/project/test-001">
                <h3>Test Project Alpha</h3>
                <p>A sample project for testing</p>
            </a>
            <a href="/project/test-002">
                <h3>Demo Application Beta</h3>
                <p>Demo application with example data</p>
            </a>
        </div>
    </body>
    </html>
    """
    
    with open(fixtures_dir / "minimal_projects_page.html", 'w') as f:
        f.write(minimal_projects)
    print("Created minimal_projects_page.html")
    
    # Create a minimal project page with knowledge files
    minimal_project = """
    <html>
    <body>
        <h1>Test Project Alpha</h1>
        <section>
            <h2>Project knowledge</h2>
            <div>
                <div data-testid="file-thumbnail">
                    <button>
                        <div>
                            <h3>example_document.txt</h3>
                            <p>150 lines</p>
                        </div>
                        <div>
                            <div>
                                <p>text</p>
                            </div>
                        </div>
                    </button>
                </div>
                <div data-testid="file-thumbnail">
                    <button>
                        <div>
                            <h3>sample_data.pdf</h3>
                            <p>75 lines</p>
                        </div>
                        <div>
                            <div>
                                <p>pdf</p>
                            </div>
                        </div>
                    </button>
                </div>
            </div>
        </section>
    </body>
    </html>
    """
    
    with open(fixtures_dir / "minimal_project_page.html", 'w') as f:
        f.write(minimal_project)
    print("Created minimal_project_page.html")


if __name__ == "__main__":
    main()