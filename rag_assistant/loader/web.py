"""
Web page document loader for cached web retrieval results.

Handles indexing of web-retrieved content with proper metadata.
"""

from pathlib import Path
from typing import List, Dict, Any
import json
from .base import BaseDocLoader


class WebDocLoader(BaseDocLoader):
    """Load cached web pages as documents."""
    
    def load(self, cache_dir: str, confidentiality: str = "public") -> List[Dict[str, Any]]:
        """
        Load all cached web pages from cache directory.
        
        Args:
            cache_dir: Path to web cache directory
            confidentiality: Confidentiality level (default: public)
            
        Returns:
            List of document chunks with metadata
        """
        chunks = []
        cache_path = Path(cache_dir)
        
        if not cache_path.exists():
            return chunks
        
        # Load all JSON cache files
        for cache_file in cache_path.glob('*.json'):
            try:
                with open(cache_file, 'r') as f:
                    cached_doc = json.load(f)
                
                # Convert cached doc to chunk format
                chunk = self._create_chunk(
                    content=cached_doc.get('content', ''),
                    source_path=cached_doc.get('source_path', ''),
                    doc_type='web',
                    page_or_section=cached_doc.get('page_or_section', 'web_result'),
                    confidentiality=confidentiality,  # Always public for web
                    domain=cached_doc.get('domain', ''),
                    url=cached_doc.get('source_path', ''),
                    cache_key=cached_doc.get('cache_key', '')
                )
                chunks.append(chunk)
            
            except Exception as e:
                print(f"Warning: Failed to load cached web page {cache_file}: {e}")
        
        return chunks