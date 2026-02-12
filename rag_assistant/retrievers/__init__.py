"""
Retrieval interface supporting both local and web sources.

Provides pluggable retriever implementations with consistent interface.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseRetriever(ABC):
    """Abstract base for all retrievers."""
    
    @abstractmethod
    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve documents matching query.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of document dicts with 'content', 'source', 'metadata'
        """
        pass