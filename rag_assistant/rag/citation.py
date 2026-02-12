"""Citation formatting with stable identifiers."""

from typing import List, Dict, Any


class CitationFormatter:
    """Formats citations from retrieved documents."""
    
    def format_bibliography(self, documents: List[Dict[str, Any]], 
                           style: str = "ieee") -> str:
        """
        Format bibliography from retrieved documents.
        
        Args:
            documents: Retrieved docs with metadata
            style: Citation style (ieee, apa)
            
        Returns:
            Formatted bibliography string
        """
        if style != "ieee":
            style = "ieee"
        
        bibliography = ["[BIBLIOGRAPHY]"]
        seen_sources = set()
        
        for i, doc in enumerate(documents, 1):
            source = doc['source_path']
            
            if source not in seen_sources:
                citation = self._format_ieee_citation(doc, i)
                bibliography.append(citation)
                seen_sources.add(source)
        
        return '\n'.join(bibliography)
    
    def _format_ieee_citation(self, doc: Dict[str, Any], index: int) -> str:
        """Format single IEEE citation."""
        source = doc['source_path']
        section = doc.get('page_or_section', 'Unknown')
        citation_id = doc.get('citation_id', f'[{index}]')
        
        return f"[{index}] {source} ({section}) - ID: {citation_id}"