"""
Citation index for fast lookups by citekey, DOI, or title.

Maintains multiple indexes for efficient search.
"""

from typing import List, Dict, Set, Optional
from collections import defaultdict
import re
from .parser import ZoteroItem


class CitationIndex:
    """
    Index for Zotero items enabling fast lookup by multiple keys.
    
    Indexes:
    - citekey (primary, unique)
    - DOI
    - title (normalized)
    - author names
    - keywords/tags
    """
    
    def __init__(self):
        """Initialize empty index."""
        self.items: Dict[str, ZoteroItem] = {}  # citekey -> item
        self.by_doi: Dict[str, str] = {}  # doi -> citekey
        self.by_title: Dict[str, List[str]] = defaultdict(list)  # title -> [citekeys]
        self.by_author: Dict[str, List[str]] = defaultdict(list)  # author -> [citekeys]
        self.by_tag: Dict[str, List[str]] = defaultdict(list)  # tag -> [citekeys]
        self.all_citekeys: Set[str] = set()
    
    def add_item(self, item: ZoteroItem):
        """
        Add item to index.
        
        Args:
            item: ZoteroItem to index
        """
        if not item.citekey:
            raise ValueError("Item must have citekey")
        
        citekey = item.citekey
        self.items[citekey] = item
        self.all_citekeys.add(citekey)
        
        # Index by DOI
        if item.doi:
            self.by_doi[item.doi.lower()] = citekey
        
        # Index by title (normalized)
        if item.title:
            normalized_title = self._normalize(item.title)
            self.by_title[normalized_title].append(citekey)
        
        # Index by authors
        for author in item.authors:
            normalized_author = self._normalize(author)
            self.by_author[normalized_author].append(citekey)
        
        # Index by tags
        for tag in item.tags:
            normalized_tag = self._normalize(tag)
            self.by_tag[normalized_tag].append(citekey)
    
    def add_items(self, items: List[ZoteroItem]):
        """
        Add multiple items to index.
        
        Args:
            items: List of ZoteroItem objects
        """
        for item in items:
            self.add_item(item)
    
    def get(self, citekey: str) -> Optional[ZoteroItem]:
        """
        Get item by citekey.
        
        Args:
            citekey: Citation key
            
        Returns:
            ZoteroItem or None if not found
        """
        return self.items.get(citekey)
    
    def search(self, query: str, limit: int = 10) -> List[ZoteroItem]:
        """
        Search for items by citekey, DOI, title, or author.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching ZoteroItem objects
        """
        normalized_query = self._normalize(query)
        results = []
        result_citekeys = set()
        
        # Exact citekey match (highest priority)
        if query in self.items:
            return [self.items[query]]
        
        # DOI match
        if query.lower() in self.by_doi:
            citekey = self.by_doi[query.lower()]
            results.append(self.items[citekey])
            result_citekeys.add(citekey)
        
        # Title matches
        for title_norm, citekeys in self.by_title.items():
            if normalized_query in title_norm or title_norm in normalized_query:
                for citekey in citekeys:
                    if citekey not in result_citekeys:
                        results.append(self.items[citekey])
                        result_citekeys.add(citekey)
                        if len(results) >= limit:
                            return results
        
        # Author matches
        for author_norm, citekeys in self.by_author.items():
            if normalized_query in author_norm or author_norm in normalized_query:
                for citekey in citekeys:
                    if citekey not in result_citekeys:
                        results.append(self.items[citekey])
                        result_citekeys.add(citekey)
                        if len(results) >= limit:
                            return results
        
        # Tag matches
        for tag_norm, citekeys in self.by_tag.items():
            if normalized_query in tag_norm or tag_norm in normalized_query:
                for citekey in citekeys:
                    if citekey not in result_citekeys:
                        results.append(self.items[citekey])
                        result_citekeys.add(citekey)
                        if len(results) >= limit:
                            return results
        
        return results[:limit]
    
    def search_advanced(self, citekey: Optional[str] = None, 
                       doi: Optional[str] = None,
                       author: Optional[str] = None,
                       year: Optional[int] = None,
                       title: Optional[str] = None) -> List[ZoteroItem]:
        """
        Advanced search with multiple criteria (AND logic).
        
        Args:
            citekey: Exact citekey match
            doi: Exact DOI match
            author: Author name substring
            year: Exact year match
            title: Title substring
            
        Returns:
            List of matching items
        """
        results = set(self.items.keys())
        
        if citekey:
            results &= {citekey} if citekey in self.items else set()
        
        if doi:
            citekey = self.by_doi.get(doi.lower())
            results &= {citekey} if citekey else set()
        
        if author:
            author_norm = self._normalize(author)
            matching_citekeys = set()
            for author_norm_idx, citekeys in self.by_author.items():
                if author_norm in author_norm_idx:
                    matching_citekeys.update(citekeys)
            results &= matching_citekeys if matching_citekeys else set()
        
        if year:
            year_citekeys = {
                ck for ck, item in self.items.items()
                if item.year == year
            }
            results &= year_citekeys
        
        if title:
            title_norm = self._normalize(title)
            title_citekeys = set()
            for title_norm_idx, citekeys in self.by_title.items():
                if title_norm in title_norm_idx:
                    title_citekeys.update(citekeys)
            results &= title_citekeys if title_citekeys else set()
        
        return [self.items[ck] for ck in results if ck in self.items]
    
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for comparison (lowercase, no special chars)."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text
    
    def get_all(self) -> List[ZoteroItem]:
        """Get all indexed items."""
        return list(self.items.values())
    
    def size(self) -> int:
        """Get total number of indexed items."""
        return len(self.items)