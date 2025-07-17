"""Additional tests to improve knowledge extractor coverage."""
import pytest
from bs4 import BeautifulSoup

from claude_sync.extractors.knowledge import KnowledgeExtractor
from claude_sync.models import KnowledgeFile


class TestKnowledgeExtractorCoverage:
    """Tests for improving knowledge extractor coverage."""
    
    def test_parse_thumbnail_entry_valid(self):
        """Test parsing valid thumbnail entries."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <h3>test_file.txt</h3>
                    <p>100 lines</p>
                </div>
                <div>
                    <div>
                        <p>text</p>
                    </div>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is not None
        assert file.name == "test_file.txt"
        assert file.lines == 100
        assert file.file_type == "text"
    
    def test_parse_thumbnail_entry_pdf(self):
        """Test parsing PDF thumbnail entry."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <h3>document.pdf</h3>
                    <p>50 lines</p>
                </div>
                <div>
                    <div>
                        <p>pdf</p>
                    </div>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is not None
        assert file.name == "document.pdf"
        assert file.lines == 50
        assert file.file_type == "pdf"
    
    def test_parse_thumbnail_entry_no_h3(self):
        """Test parsing thumbnail without h3 tag."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <p>100 lines</p>
                    <p>text</p>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is None
    
    def test_parse_thumbnail_entry_empty_name(self):
        """Test parsing thumbnail with empty name."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <h3>   </h3>
                    <p>100 lines</p>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is None
    
    def test_parse_thumbnail_entry_no_lines(self):
        """Test parsing thumbnail without line count."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <h3>test.txt</h3>
                    <p>Some other text</p>
                </div>
                <div>
                    <div>
                        <p>text</p>
                    </div>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is not None
        assert file.name == "test.txt"
        assert file.lines is None
        assert file.file_type == "text"
    
    def test_parse_thumbnail_entry_malformed_lines(self):
        """Test parsing thumbnail with malformed line count."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <h3>test.txt</h3>
                    <p>abc lines</p>
                </div>
                <div>
                    <div>
                        <p>text</p>
                    </div>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is not None
        assert file.lines is None  # Malformed lines should result in None
    
    def test_parse_thumbnail_entry_no_file_type(self):
        """Test parsing thumbnail without explicit file type."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <h3>mystery_file</h3>
                    <p>100 lines</p>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is not None
        assert file.name == "mystery_file"
        assert file.lines == 100
        assert file.file_type == "text"  # Defaults to text when lines are present
    
    def test_parse_thumbnail_entry_no_type_no_lines(self):
        """Test parsing thumbnail without type or lines."""
        html = """
        <div data-testid="file-thumbnail">
            <button>
                <div>
                    <h3>mystery_file</h3>
                </div>
            </button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        thumbnail = soup.find('div', {'data-testid': 'file-thumbnail'})
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(thumbnail)
        
        assert file is None  # Can't determine file type
    
    def test_parse_thumbnail_entry_exception(self):
        """Test handling exceptions in thumbnail parsing."""
        # Pass None to trigger exception
        extractor = KnowledgeExtractor()
        file = extractor._parse_thumbnail_entry(None)
        
        assert file is None
    
    def test_extract_thumbnails_at_root(self):
        """Test extracting thumbnails at root level (strategy 1)."""
        html = """
        <html><body>
            <div data-testid="file-thumbnail">
                <button>
                    <div>
                        <h3>file1.txt</h3>
                        <p>100 lines</p>
                    </div>
                    <div><div><p>text</p></div></div>
                </button>
            </div>
            <div data-testid="file-thumbnail">
                <button>
                    <div>
                        <h3>file2.pdf</h3>
                        <p>200 lines</p>
                    </div>
                    <div><div><p>pdf</p></div></div>
                </button>
            </div>
        </body></html>
        """
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(html)
        
        assert len(files) == 2
        assert files[0].name == "file1.txt"
        assert files[1].name == "file2.pdf"
    
    def test_extract_thumbnails_in_section(self):
        """Test extracting thumbnails within knowledge section (strategy 2)."""
        html = """
        <html><body>
            <section>
                <h2>Project knowledge</h2>
                <div>
                    <div data-testid="file-thumbnail">
                        <button>
                            <div>
                                <h3>section_file.txt</h3>
                                <p>150 lines</p>
                            </div>
                            <div><div><p>text</p></div></div>
                        </button>
                    </div>
                </div>
            </section>
        </body></html>
        """
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(html)
        
        assert len(files) == 1
        assert files[0].name == "section_file.txt"
        assert files[0].lines == 150
    
    def test_find_knowledge_container_section(self):
        """Test finding knowledge container as section."""
        html = """
        <section>
            <h2>Project knowledge</h2>
            <div data-testid="file-thumbnail"></div>
        </section>
        """
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        
        extractor = KnowledgeExtractor()
        container = extractor._find_knowledge_container(header)
        
        assert container is not None
        assert container.name == 'section'
    
    def test_find_knowledge_container_parent_search(self):
        """Test finding knowledge container by searching parents."""
        html = """
        <div class="outer">
            <h2>Project knowledge</h2>
            <ul class="grid files">
                <li>file1</li>
            </ul>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        
        extractor = KnowledgeExtractor()
        container = extractor._find_knowledge_container(header)
        
        assert container is not None
        assert 'outer' in container.get('class', [])
    
    def test_find_knowledge_container_file_item_parent(self):
        """Test finding container with file-item class."""
        html = """
        <div class="container">
            <h2>Project knowledge</h2>
            <div class="file-item">file</div>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        
        extractor = KnowledgeExtractor()
        container = extractor._find_knowledge_container(header)
        
        assert container is not None
        assert container.find('div', class_='file-item') is not None
    
    def test_find_knowledge_container_fallback(self):
        """Test fallback to immediate parent."""
        html = """
        <div>
            <h2>Project knowledge</h2>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        header = soup.find('h2')
        
        extractor = KnowledgeExtractor()
        container = extractor._find_knowledge_container(header)
        
        assert container is not None
        assert container == header.parent
    
    def test_parse_file_entry_without_button(self):
        """Test parsing file entry without button."""
        html = """
        <div class="file-item">
            <span>Not a file</span>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_file_entry(div)
        
        assert file is None
    
    def test_parse_file_entry_empty_contents(self):
        """Test parsing file entry with empty contents."""
        html = """<div class="file-item"></div>"""
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_file_entry(div)
        
        assert file is None
    
    def test_parse_file_entry_no_text_parts(self):
        """Test parsing file entry with no text content."""
        html = """
        <div class="file-item">
            <button>Click me</button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_file_entry(div)
        
        assert file is None
    
    def test_parse_file_entry_no_valid_name(self):
        """Test parsing file entry without valid name."""
        html = """
        <div class="file-item">
            Select file
            100 lines
            TEXT
            <button>Open</button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_file_entry(div)
        
        assert file is None
    
    def test_parse_file_entry_tag_text(self):
        """Test parsing file entry with text in tags."""
        html = """
        <div class="file-item">
            <span>Tagged file.txt</span>
            <em>50 lines</em>
            <strong>PDF</strong>
            <button>Open</button>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        
        extractor = KnowledgeExtractor()
        file = extractor._parse_file_entry(div)
        
        assert file is not None
        assert file.name == "Tagged file.txt"
        assert file.lines == 50
        assert file.file_type == "pdf"
    
    def test_extract_fallback_to_file_items(self):
        """Test extraction falling back to file-item divs."""
        html = """
        <html><body>
            <section>
                <h2>Project knowledge</h2>
                <div>
                    <div class="file-item">
                        Old format file.txt
                        25 lines
                        TEXT
                        <button>Open</button>
                    </div>
                </div>
            </section>
        </body></html>
        """
        extractor = KnowledgeExtractor()
        files = extractor.extract_from_html(html)
        
        assert len(files) == 1
        assert files[0].name == "Old format file.txt"
        assert files[0].lines == 25