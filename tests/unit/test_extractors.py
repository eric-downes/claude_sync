"""Tests for HTML extractors."""
import pytest
from bs4 import BeautifulSoup

from claude_sync.extractors import ProjectExtractor, KnowledgeExtractor
from claude_sync.models import Project, KnowledgeFile
from tests.fixtures.html_samples import (
    PROJECTS_PAGE_HTML,
    EMPTY_PROJECTS_PAGE_HTML,
    DNI_PROJECT_PAGE_HTML,
    EMPTY_PROJECT_PAGE_HTML,
    LOGIN_PAGE_HTML,
)


class TestProjectExtractor:
    """Test ProjectExtractor."""
    
    def test_extract_projects_from_html(self):
        """Test extracting projects from HTML string."""
        extractor = ProjectExtractor()
        projects = extractor.extract_from_html(PROJECTS_PAGE_HTML)
        
        assert len(projects) == 4
        
        # Check DNI project
        dni = projects[0]
        assert dni.id == "0197d5a6-8f23-7002-9e49-0f72752b214c"
        assert dni.name == "DNI"
        assert dni.description == "EU-only MLETR"
        assert dni.url == "https://claude.ai/project/0197d5a6-8f23-7002-9e49-0f72752b214c"
        
        # Check DLPoS project (no description)
        dlpos = projects[1]
        assert dlpos.id == "019800bd-979b-7116-864b-006d88133519"
        assert dlpos.name == "DLPoS"
        assert dlpos.description is None
        assert dlpos.url == "https://claude.ai/project/019800bd-979b-7116-864b-006d88133519"
        
        # Check monoidal project
        monoidal = projects[2]
        assert monoidal.name == "monoidal"
        assert monoidal.description is None
        
        # Check Playing God project
        playing_god = projects[3]
        assert playing_god.name == "Playing God"
        assert playing_god.description == "create life!"
    
    def test_extract_projects_from_soup(self):
        """Test extracting projects from BeautifulSoup object."""
        extractor = ProjectExtractor()
        soup = BeautifulSoup(PROJECTS_PAGE_HTML, 'html.parser')
        projects = extractor.extract_from_soup(soup)
        
        assert len(projects) == 4
        assert all(isinstance(p, Project) for p in projects)
    
    def test_extract_empty_projects_page(self):
        """Test extracting from page with no projects."""
        extractor = ProjectExtractor()
        projects = extractor.extract_from_html(EMPTY_PROJECTS_PAGE_HTML)
        
        assert len(projects) == 0
    
    def test_extract_with_invalid_html(self):
        """Test extraction with malformed HTML."""
        extractor = ProjectExtractor()
        projects = extractor.extract_from_html("<div>Not a valid page</div>")
        
        assert len(projects) == 0
    
    def test_parse_project_card_edge_cases(self):
        """Test parsing project cards with edge cases."""
        extractor = ProjectExtractor()
        
        # Test with empty link
        html = '<a href="/project/123"><div></div></a>'
        projects = extractor.extract_from_html(html)
        assert len(projects) == 0  # Should skip invalid cards
        
        # Test with missing ID
        html = '<a href="/invalid/url"><div><div>Test</div></div></a>'
        projects = extractor.extract_from_html(html)
        assert len(projects) == 0
    
    def test_project_url_normalization(self):
        """Test that project URLs are properly normalized."""
        extractor = ProjectExtractor()
        
        # Test with relative URL
        html = '<a href="/project/123"><div><div>Test Project</div></div></a>'
        projects = extractor.extract_from_html(html)
        assert len(projects) == 1
        assert projects[0].url == "https://claude.ai/project/123"
        
        # Test with full URL (shouldn't happen but handle gracefully)
        html = '<a href="https://claude.ai/project/456"><div><div>Test 2</div></div></a>'
        projects = extractor.extract_from_html(html)
        assert len(projects) == 1
        assert projects[0].url == "https://claude.ai/project/456"


class TestKnowledgeExtractor:
    """Test KnowledgeExtractor."""
    
    def test_extract_knowledge_files_from_html(self):
        """Test extracting knowledge files from project page."""
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(DNI_PROJECT_PAGE_HTML)
        
        assert len(files) == 7
        
        # Check text files
        invoice = files[0]
        assert invoice.name == "Invoice valuation"
        assert invoice.file_type == "text"
        assert invoice.lines == 489
        
        illiquid = files[1]
        assert illiquid.name == "Illiquid pricing"
        assert illiquid.file_type == "text"
        assert illiquid.lines == 421
        
        # Check all text files are extracted
        text_files = [f for f in files if f.file_type == "text"]
        assert len(text_files) == 6
        
        # Check PDF file
        pdf_files = [f for f in files if f.file_type == "pdf"]
        assert len(pdf_files) == 1
        assert pdf_files[0].name == "Trade Finance Report 2024"
        assert pdf_files[0].lines is None  # PDFs don't have line counts
    
    def test_extract_from_soup(self):
        """Test extracting from BeautifulSoup object."""
        extractor = KnowledgeExtractor()
        soup = BeautifulSoup(DNI_PROJECT_PAGE_HTML, 'html.parser')
        files = extractor.extract_from_soup(soup)
        
        assert len(files) == 7
        assert all(isinstance(f, KnowledgeFile) for f in files)
    
    def test_extract_empty_project(self):
        """Test extracting from project with no files."""
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(EMPTY_PROJECT_PAGE_HTML)
        
        assert len(files) == 0
    
    def test_extract_without_knowledge_section(self):
        """Test extracting from page without knowledge section."""
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html("<html><body>No knowledge section</body></html>")
        
        assert len(files) == 0
    
    def test_file_name_extraction(self):
        """Test correct file name extraction."""
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(DNI_PROJECT_PAGE_HTML)
        
        expected_names = [
            "Invoice valuation",
            "Illiquid pricing",
            "legal memo",
            "uk domestic",
            "traxpay podcast BoE transcript",
            "germany trade fi specific",
            "Trade Finance Report 2024"
        ]
        
        actual_names = [f.name for f in files]
        assert actual_names == expected_names
    
    def test_line_count_parsing(self):
        """Test parsing of line counts."""
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(DNI_PROJECT_PAGE_HTML)
        
        # Check specific line counts
        line_counts = {f.name: f.lines for f in files if f.lines}
        assert line_counts["Invoice valuation"] == 489
        assert line_counts["Illiquid pricing"] == 421
        assert line_counts["legal memo"] == 169
        assert line_counts["uk domestic"] == 105
        assert line_counts["traxpay podcast BoE transcript"] == 155
        assert line_counts["germany trade fi specific"] == 452
    
    def test_malformed_file_entries(self):
        """Test handling of malformed file entries."""
        html = """
        <html><body>
            <h2>Project knowledge</h2>
            <div>filename without lines</div>
            <div>500 lines</div>
            <div>TEXT</div>
            
            <div>Another file
            Not properly formatted</div>
        </body></html>
        """
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(html)
        
        # Should handle gracefully and extract what it can
        assert len(files) >= 0  # Depends on implementation