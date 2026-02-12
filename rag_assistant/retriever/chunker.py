"""
Text chunking strategies for document segmentation.
"""

from typing import List, Dict, Any


class TextChunker:
    """Chunks text into overlapping segments for embedding."""
    
    def __init__(self, chunk_size: int = 512, overlap: int = 100):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters.
            overlap: Overlap between consecutive chunks.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, source: str = "unknown") -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping segments.
        
        Args:
            text: Text to chunk.
            source: Source reference for chunks.
            
        Returns:
            List of chunk dictionaries with content and metadata.
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            
            chunks.append({
                'content': chunk_text,
                'source': source,
                'chunk_index': len(chunks)
            })
            
            start = end - self.overlap
        
        return chunks