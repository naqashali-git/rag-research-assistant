"""Tests for paper drafting functionality."""

import pytest
import tempfile
from pathlib import Path
from rag_assistant.paper import (
    OutlineGenerator,
    PaperOutline,
    Section,
    PaperDraftEngine,
)
from rag_assistant.paper.formatter_latex import LaTeXFormatter
from rag_assistant.paper.formatter_docx import DocXFormatter


class TestOutlineGeneration:
    """Tests for IEEE outline generation."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM for testing."""
        class MockLLM:
            def generate(self, prompt, temperature=0.7, max_tokens=1024):
                # Return minimal outline
                outline_text = """
## Introduction
- Important background concept
- Research motivation
- Problem statement

## Related Work
- Previous approaches
- State of the art
- Gaps in literature

## Proposed Approach
- Novel methodology
- Technical contribution
- Implementation details

## Results
- Experimental setup
- Performance metrics
- Comparative analysis
"""
                return {
                    'text': outline_text,
                    'tokens': 100,
                    'time_ms': 500
                }
        
        return MockLLM()
    
    def test_outline_generation(self, mock_llm):
        """Test outline generation."""
        generator = OutlineGenerator(mock_llm)
        
        outline = generator.generate_outline(
            "Machine Learning Fundamentals",
            num_sections=4,
            include_related_work=True,
            deterministic=True
        )
        
        assert outline.title == "Machine Learning Fundamentals"
        assert len(outline.sections) > 0
        assert any(s.title == "Introduction" for s in outline.sections)
    
    def test_outline_to_markdown(self, mock_llm):
        """Test outline Markdown export."""
        outline = PaperOutline(
            title="Test Paper",
            abstract="This is a test.",
            sections=[
                Section(
                    title="Introduction",
                    level=1,
                    bullet_points=["Point 1", "Point 2"]
                ),
                Section(
                    title="Conclusion",
                    level=1,
                    bullet_points=["Conclusion point"]
                )
            ]
        )
        
        markdown = outline.to_markdown()
        
        assert "# Test Paper" in markdown
        assert "## Introduction" in markdown
        assert "- Point 1" in markdown


class TestLatexFormatting:
    """Tests for LaTeX output."""
    
    def test_latex_generation(self):
        """Test LaTeX file generation."""
        from rag_assistant.paper.engine import DraftedSection
        
        outline = PaperOutline(
            title="Test Paper",
            abstract="Abstract",
            sections=[
                Section(title="Introduction", level=1),
                Section(title="Conclusion", level=1)
            ]
        )
        
        sections = [
            DraftedSection(
                title="Introduction",
                level=1,
                content="This is the introduction.",
                citations=[],
                word_count=5,
                generation_time_ms=100
            ),
            DraftedSection(
                title="Conclusion",
                level=1,
                content="This is the conclusion.",
                citations=[],
                word_count=4,
                generation_time_ms=100
            )
        ]
        
        citations = []
        
        main_tex, references_bib = LaTeXFormatter.format_paper(
            outline, sections, citations
        )
        
        assert r"\documentclass[conference]{IEEEtran}" in main_tex
        assert r"\section{Introduction}" in main_tex
        assert r"\bibliography{references}" in main_tex
    
    def test_latex_special_char_escaping(self):
        """Test LaTeX special character escaping."""
        escaped = LaTeXFormatter._escape_latex("Test & 50% $cost #1")
        
        assert r"\&" in escaped
        assert r"\%" in escaped
        assert r"\$" in escaped
        assert r"\#" in escaped
    
    def test_latex_file_save(self):
        """Test saving LaTeX files."""
        from rag_assistant.paper.engine import DraftedSection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            outline = PaperOutline(title="Test")
            sections = [
                DraftedSection(
                    title="Test",
                    level=1,
                    content="Content",
                    citations=[],
                    word_count=1,
                    generation_time_ms=100
                )
            ]
            
            LaTeXFormatter.save_to_files(
                outline, sections, [], tmpdir
            )
            
            assert (Path(tmpdir) / 'main.tex').exists()
            assert (Path(tmpdir) / 'references.bib').exists()


class TestDocXFormatting:
    """Tests for Word document generation."""
    
    def test_docx_clean_generation(self):
        """Test clean DOCX generation (fallback)."""
        from rag_assistant.paper.engine import DraftedSection
        
        outline = PaperOutline(
            title="Test Paper",
            abstract="This is a test."
        )
        
        sections = [
            DraftedSection(
                title="Introduction",
                level=1,
                content="Introduction content.",
                citations=[],
                word_count=2,
                generation_time_ms=100
            )
        ]
        
        citations = []
        
        doc = DocXFormatter.format_paper_clean(outline, sections, citations)
        
        # Verify document was created
        assert doc is not None
        assert len(doc.paragraphs) > 0
    
    def test_docx_file_save(self):
        """Test saving DOCX file."""
        from rag_assistant.paper.engine import DraftedSection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            outline = PaperOutline(title="Test Paper")
            sections = [
                DraftedSection(
                    title="Test",
                    level=1,
                    content="Content",
                    citations=[],
                    word_count=1,
                    generation_time_ms=100
                )
            ]
            
            doc = DocXFormatter.format_paper_clean(outline, sections, [])
            
            output_file = Path(tmpdir) / "test.docx"
            DocXFormatter.save_to_file(doc, str(output_file))
            
            assert output_file.exists()


class TestDeterministicMode:
    """Tests for deterministic (temperature=0) output."""
    
    def test_deterministic_flag(self):
        """Test that deterministic flag is passed correctly."""
        
        class TrackingLLM:
            def __init__(self):
                self.last_temperature = None
            
            def generate(self, prompt, temperature=0.7, max_tokens=1024):
                self.last_temperature = temperature
                return {
                    'text': "## Section\n- Point 1",
                    'tokens': 10,
                    'time_ms': 100
                }
        
        llm = TrackingLLM()
        generator = OutlineGenerator(llm)
        
        # Deterministic (temperature=0)
        generator.generate_outline("Test", deterministic=True)
        assert llm.last_temperature == 0.0
        
        # Non-deterministic
        generator.generate_outline("Test", deterministic=False)
        assert llm.last_temperature != 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])