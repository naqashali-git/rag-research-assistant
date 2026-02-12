"""DOCX document loader using python-docx."""

from pathlib import Path
from typing import List, Dict, Any
from docx import Document
from .base import BaseDocLoader


class DOCXDocLoader(BaseDocLoader):
    """Load and parse DOCX (Word) documents with metadata."""
    
    def load(self, path: str, confidentiality: str = "internal") -> List[Dict[str, Any]]:
        """
        Load DOCX and extract text by section.
        
        Args:
            path: Path to DOCX file
            confidentiality: Confidentiality level for chunks
            
        Returns:
            List of section chunks with metadata
            
        Raises:
            FileNotFoundError: If DOCX not found
            ValueError: If DOCX invalid
        """
        docx_path = Path(path)
        
        if not docx_path.exists():
            raise FileNotFoundError(f"DOCX not found: {path}")
        
        chunks = []
        
        try:
            doc = Document(docx_path)
            
            current_heading = "Introduction"
            section_content = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                
                if not text:
                    continue
                
                # Detect heading
                if para.style.name.startswith('Heading'):
                    # Save previous section
                    if section_content:
                        chunk = self._create_chunk(
                            content='\n'.join(section_content),
                            source_path=str(docx_path),
                            doc_type='docx',
                            page_or_section=current_heading,
                            confidentiality=confidentiality
                        )
                        chunks.append(chunk)
                    
                    current_heading = text
                    section_content = []
                else:
                    section_content.append(text)
            
            # Save final section
            if section_content:
                chunk = self._create_chunk(
                    content='\n'.join(section_content),
                    source_path=str(docx_path),
                    doc_type='docx',
                    page_or_section=current_heading,
                    confidentiality=confidentiality
                )
                chunks.append(chunk)
        
        except Exception as e:
            raise ValueError(f"Error reading DOCX: {e}")
        
        return chunks