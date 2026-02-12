"""Markdown and plain text document loader."""

from pathlib import Path
from typing import List, Dict, Any
import re
from .base import BaseDocLoader


class MarkdownDocLoader(BaseDocLoader):
    """Load and parse Markdown/TXT documents with metadata."""
    
    def load(self, path: str, confidentiality: str = "internal") -> List[Dict[str, Any]]:
        """
        Load Markdown/TXT and extract text by section.
        
        Args:
            path: Path to Markdown or TXT file
            confidentiality: Confidentiality level for chunks
            
        Returns:
            List of section chunks with metadata
            
        Raises:
            FileNotFoundError: If file not found
        """
        file_path = Path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by markdown headings (# ## ###)
            sections = re.split(r'\n(#{1,6} .+)\n', content)
            
            current_heading = 'Introduction'
            
            for i in range(1, len(sections), 2):
                if i < len(sections):
                    heading_text = sections[i].lstrip('#').strip()
                    body_text = sections[i + 1].strip() if i + 1 < len(sections) else ''
                    
                    if body_text:
                        chunk = self._create_chunk(
                            content=body_text,
                            source_path=str(file_path),
                            doc_type='markdown' if path.endswith('.md') else 'text',
                            page_or_section=heading_text,
                            confidentiality=confidentiality
                        )
                        chunks.append(chunk)
                        current_heading = heading_text
            
            # If no sections found, treat as single chunk
            if not chunks and content.strip():
                chunk = self._create_chunk(
                    content=content,
                    source_path=str(file_path),
                    doc_type='markdown' if path.endswith('.md') else 'text',
                    page_or_section='Full Document',
                    confidentiality=confidentiality
                )
                chunks.append(chunk)
        
        except Exception as e:
            raise ValueError(f"Error reading file: {e}")
        
        return chunks