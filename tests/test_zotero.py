"""Tests for Zotero citation management."""

import pytest
import json
import tempfile
from pathlib import Path
from rag_assistant.zotero import (
    parse_zotero_export,
    ZoteroItem,
    CitationIndex,
    BibTeXFormatter,
    FormattedCitationFormatter
)
from rag_assistant.zotero.parser import BetterBibTeXParser, BibTeXFileParser


# Sample Better BibTeX JSON export
SAMPLE_BETTER_BIBTEX_JSON = [
    {
        "key": "item-1",
        "citationKey": "Doe2023",
        "title": "Machine Learning Fundamentals",
        "creators": [
            {"family": "Doe", "given": "John"},
            {"family": "Smith", "given": "Jane"}
        ],
        "issued": {"date-parts": [[2023]]},
        "type": "journal-article",
        "journal": "AI Research Quarterly",
        "volume": "42",
        "issue": "3",
        "pages": "123-145",
        "DOI": "10.1234/ai.2023.42",
        "URL": "https://example.com/paper",
        "abstract": "This paper explores fundamental concepts in machine learning."
    },
    {
        "key": "item-2",
        "citationKey": "Lewis2020",
        "title": "Retrieval-Augmented Generation",
        "creators": [
            {"family": "Lewis", "given": "Patrick"}
        ],
        "issued": {"date-parts": [[2020]]},
        "type": "conference",
        "bookTitle": "Proceedings of NeurIPS",
        "pages": "1234-1246",
        "abstract": "We introduce RAG for knowledge-intensive tasks."
    }
]

# Sample BibTeX file
SAMPLE_BIBTEX = """
@article{Doe2023,
  author = {Doe, John and Smith, Jane},
  title = {Machine Learning Fundamentals},
  journal = {AI Research Quarterly},
  year = {2023},
  volume = {42},
  number = {3},
  pages = {123--145},
  doi = {10.1234/ai.2023.42}
}

@inproceedings{Lewis2020,
  author = {Lewis, Patrick},
  title = {Retrieval-Augmented Generation},
  booktitle = {Proceedings of NeurIPS},
  year = {2020},
  pages = {1234--1246}
}
"""


class TestBetterBibTeXParser:
    """Tests for Better BibTeX JSON parsing."""
    
    def test_parse_json_items(self):
        """Test parsing Better BibTeX JSON."""
        items = BetterBibTeXParser.parse(SAMPLE_BETTER_BIBTEX_JSON)
        
        assert len(items) == 2
        
        # Check first item
        item1 = items[0]
        assert item1.citekey == "Doe2023"
        assert item1.title == "Machine Learning Fundamentals"
        assert len(item1.authors) == 2
        assert item1.year == 2023
        assert item1.doi == "10.1234/ai.2023.42"
        assert item1.journal == "AI Research Quarterly"
    
    def test_parse_json_string(self):
        """Test parsing JSON string."""
        json_str = json.dumps(SAMPLE_BETTER_BIBTEX_JSON)
        items = BetterBibTeXParser.parse(json_str)
        
        assert len(items) == 2
        assert items[0].citekey == "Doe2023"
    
    def test_parse_json_invalid(self):
        """Test error handling for invalid JSON."""
        with pytest.raises(ValueError):
            BetterBibTeXParser.parse("{invalid json")
    
    def test_author_parsing(self):
        """Test author field parsing."""
        items = BetterBibTeXParser.parse(SAMPLE_BETTER_BIBTEX_JSON)
        
        item1 = items[0]
        assert "John Doe" in item1.authors
        assert "Jane Smith" in item1.authors
        
        item2 = items[1]
        assert "Patrick Lewis" in item2.authors


class TestBibTeXFileParser:
    """Tests for BibTeX file parsing."""
    
    def test_parse_bibtex_content(self):
        """Test parsing BibTeX file content."""
        items = BibTeXFileParser.parse(SAMPLE_BIBTEX)
        
        assert len(items) == 2
        
        # Check first entry
        item1 = items[0]
        assert item1.citekey == "Doe2023"
        assert item1.title == "Machine Learning Fundamentals"
        assert item1.year == 2023
        assert item1.item_type == "article"
    
    def test_author_parsing_bibtex(self):
        """Test author parsing from BibTeX."""
        items = BibTeXFileParser.parse(SAMPLE_BIBTEX)
        
        item1 = items[0]
        assert "Doe, John" in item1.authors
        assert "Smith, Jane" in item1.authors
    
    def test_conference_paper_parsing(self):
        """Test conference paper parsing."""
        items = BibTeXFileParser.parse(SAMPLE_BIBTEX)
        
        item2 = items[1]
        assert item2.item_type == "inproceedings"
        assert item2.booktitle == "Proceedings of NeurIPS"


class TestZoteroItemConversion:
    """Tests for ZoteroItem conversion."""
    
    def test_to_bibtex(self):
        """Test conversion to BibTeX format."""
        item = ZoteroItem(
            key="test-1",
            citekey="Test2023",
            title="Test Paper",
            authors=["John Doe", "Jane Smith"],
            year=2023,
            item_type="article",
            journal="Test Journal",
            volume="10",
            pages="1-10"
        )
        
        bibtex = item.to_bibtex()
        
        assert "@article{Test2023," in bibtex
        assert "title = {Test Paper}" in bibtex
        assert "author = {John Doe and Jane Smith}" in bibtex
        assert "year = {2023}" in bibtex
        assert "journal = {Test Journal}" in bibtex
    
    def test_short_citation(self):
        """Test short citation generation."""
        item = ZoteroItem(
            key="test-1",
            citekey="Test2023",
            title="Test",
            authors=["John Doe", "Jane Smith"],
            year=2023,
            item_type="article"
        )
        
        short = item.short_citation()
        assert "Doe" in short
        assert "et al." in short
        assert "2023" in short
    
    def test_author_string(self):
        """Test author string formatting."""
        item = ZoteroItem(
            key="test-1",
            citekey="Test2023",
            title="Test",
            authors=["John Doe", "Jane Smith"],
            item_type="article"
        )
        
        author_str = item.author_string()
        assert author_str == "John Doe, Jane Smith"


class TestCitationIndex:
    """Tests for citation indexing."""
    
    @pytest.fixture
    def index_with_items(self):
        """Create index with sample items."""
        items = BetterBibTeXParser.parse(SAMPLE_BETTER_BIBTEX_JSON)
        index = CitationIndex()
        index.add_items(items)
        return index
    
    def test_index_creation(self, index_with_items):
        """Test index initialization."""
        assert index_with_items.size() == 2
        assert "Doe2023" in index_with_items.all_citekeys
        assert "Lewis2020" in index_with_items.all_citekeys
    
    def test_get_by_citekey(self, index_with_items):
        """Test retrieval by citekey."""
        item = index_with_items.get("Doe2023")
        
        assert item is not None
        assert item.title == "Machine Learning Fundamentals"
    
    def test_search_by_title(self, index_with_items):
        """Test search by title."""
        results = index_with_items.search("Machine Learning")
        
        assert len(results) > 0
        assert results[0].citekey == "Doe2023"
    
    def test_search_by_author(self, index_with_items):
        """Test search by author."""
        results = index_with_items.search("Lewis")
        
        assert len(results) > 0
        assert results[0].citekey == "Lewis2020"
    
    def test_search_limit(self, index_with_items):
        """Test search result limiting."""
        results = index_with_items.search("", limit=1)
        
        assert len(results) <= 1
    
    def test_advanced_search(self, index_with_items):
        """Test advanced search with multiple criteria."""
        results = index_with_items.search_advanced(year=2023)
        
        assert len(results) > 0
        assert all(r.year == 2023 for r in results)


class TestBibTeXFormatter:
    """Tests for BibTeX formatting."""
    
    def test_generate_complete_bibtex(self):
        """Test complete BibTeX file generation."""
        items = BetterBibTeXParser.parse(SAMPLE_BETTER_BIBTEX_JSON)
        
        bibtex = BibTeXFormatter.generate(items)
        
        assert "@" in bibtex
        assert "Doe2023" in bibtex
        assert "Lewis2020" in bibtex
        assert "Generated by RAG Research Assistant" in bibtex
    
    def test_generate_without_header(self):
        """Test BibTeX generation without header."""
        items = BetterBibTeXParser.parse(SAMPLE_BETTER_BIBTEX_JSON)
        
        bibtex = BibTeXFormatter.generate(items, include_header=False)
        
        assert "Generated by" not in bibtex
        assert "@" in bibtex


class TestFormattedCitationFormatter:
    """Tests for formatted citation output."""
    
    @pytest.fixture
    def sample_items(self):
        """Get sample items."""
        return BetterBibTeXParser.parse(SAMPLE_BETTER_BIBTEX_JSON)
    
    def test_ieee_numeric_format(self, sample_items):
        """Test IEEE numeric citation format."""
        formatted = FormattedCitationFormatter.format_ieee_numeric(sample_items)
        
        assert "[1]" in formatted
        assert "[2]" in formatted
        assert "Doe" in formatted
        assert "Lewis" in formatted
    
    def test_apa_format(self, sample_items):
        """Test APA citation format."""
        formatted = FormattedCitationFormatter.format_apa_style(sample_items)
        
        assert "Doe" in formatted
        assert "2023" in formatted
    
    def test_html_format(self, sample_items):
        """Test HTML list format."""
        formatted = FormattedCitationFormatter.format_html_list(sample_items)
        
        assert "<ol>" in formatted
        assert "<li>" in formatted
        assert "</ol>" in formatted
    
    def test_markdown_format(self, sample_items):
        """Test Markdown list format."""
        formatted = FormattedCitationFormatter.format_markdown_list(sample_items)
        
        assert "1. " in formatted
        assert "2. " in formatted
        assert "Doe" in formatted


class TestFileFormatDetection:
    """Tests for auto-detecting file formats."""
    
    def test_detect_json_format(self):
        """Test JSON format detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "zotero.json"
            json_file.write_text(json.dumps(SAMPLE_BETTER_BIBTEX_JSON))
            
            items = parse_zotero_export(str(json_file))
            
            assert len(items) == 2
            assert items[0].citekey == "Doe2023"
    
    def test_detect_bibtex_format(self):
        """Test BibTeX format detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bib_file = Path(tmpdir) / "references.bib"
            bib_file.write_text(SAMPLE_BIBTEX)
            
            items = parse_zotero_export(str(bib_file))
            
            assert len(items) == 2
            assert items[0].citekey == "Doe2023"


class TestIntegration:
    """Integration tests for full Zotero workflow."""
    
    def test_load_and_export_workflow(self):
        """Test loading Zotero and exporting BibTeX."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Load
            json_file = Path(tmpdir) / "zotero.json"
            json_file.write_text(json.dumps(SAMPLE_BETTER_BIBTEX_JSON))
            
            items = parse_zotero_export(str(json_file))
            
            # Export
            bibtex = BibTeXFormatter.generate(items)
            
            # Verify
            assert "@article{Doe2023," in bibtex
            assert "@conference{Lewis2020," in bibtex or "@inproceedings{Lewis2020," in bibtex
    
    def test_search_and_format_workflow(self):
        """Test searching index and formatting results."""
        items = BetterBibTeXParser.parse(SAMPLE_BETTER_BIBTEX_JSON)
        index = CitationIndex()
        index.add_items(items)
        
        # Search
        results = index.search("machine learning")
        
        # Format
        formatted = FormattedCitationFormatter.format_ieee_numeric(results)
        
        # Verify
        assert "[1]" in formatted
        assert "Machine Learning" in formatted


if __name__ == '__main__':
    pytest.main([__file__, '-v'])