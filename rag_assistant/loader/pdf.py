"""PDF document loader using PyPDF2."""

from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
from .base import BaseDocLoader


class PDFDocLoader(BaseDocLoader):
    """Load and parse PDF documents with metadata."""
    
    def load(self, path: str, confidentiality: str = "internal") -> List[Dict[str, Any]]:
        """
        Load PDF and extract text by page.
        
        Args:
            path: Path to PDF file
            confidentiality: Confidentiality level for chunks
            
        Returns:
            List of page chunks with metadata
            
        Raises:
            FileNotFoundError: If PDF not found
            ValueError: If PDF invalid
        """
        pdf_path = Path(path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        
        chunks = []
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    text = page.extract_text()
                    
                    if text.strip():
                        chunk = self._create_chunk(
                            content=text,
                            source_path=str(pdf_path),
                            doc_type='pdf',
                            page_or_section=f"page_{page_num}",
                            confidentiality=confidentiality,
                            total_pages=len(pdf_reader.pages)
                        )
                        chunks.append(chunk)
        
        except PyPDF2.errors.PdfReadError as e:
            raise ValueError(f"Invalid PDF: {e}")
        except Exception as e:
            raise ValueError(f"Error reading PDF: {e}")
        
        return chunks