"""
Base document loader interface with mandatory metadata schema.

All chunks must include:
- source_path: original file path
- doc_type: pdf, docx, markdown, zotero
- page_or_section: page number or heading
- created_at: ISO 8601 timestamp
- hash: SHA256 of chunk content
- confidentiality: internal, confidential, public
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
import hashlib


class BaseDocLoader(ABC):
    """Abstract base for document loaders with mandatory metadata."""
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """
        Compute SHA256 hash of chunk content.
        
        Args:
            content: Chunk text
            
        Returns:
            Hex-encoded SHA256 hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @abstractmethod
    def load(self, path: str) -> List[Dict[str, Any]]:
        """
        Load document and return chunks with complete metadata.
        
        Args:
            path: Path to document
            
        Returns:
            List of chunks, each with structure:
            {
                'content': str,
                'metadata': {
                    'source_path': str,
                    'doc_type': str,
                    'page_or_section': str,
                    'created_at': str,  # ISO 8601
                    'hash': str,  # SHA256
                    'confidentiality': str,
                    ... (doc-specific fields)
                }
            }
        """
        pass
    
    def _create_chunk(self, content: str, source_path: str, doc_type: str,
                     page_or_section: str, confidentiality: str = "internal",
                     **extra_metadata) -> Dict[str, Any]:
        """
        Create a chunk with mandatory metadata schema.
        
        Args:
            content: Chunk text content
            source_path: Original file path
            doc_type: Type of document (pdf, docx, markdown, zotero)
            page_or_section: Page number or section heading
            confidentiality: internal, confidential, public
            **extra_metadata: Additional metadata fields
            
        Returns:
            Chunk dict with complete metadata
        """
        metadata = {
            'source_path': source_path,
            'doc_type': doc_type,
            'page_or_section': page_or_section,
            'created_at': datetime.utcnow().isoformat(),
            'hash': self.compute_hash(content),
            'confidentiality': confidentiality,
            **extra_metadata
        }
        
        return {
            'content': content,
            'metadata': metadata
        }