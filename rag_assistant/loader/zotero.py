"""
Zotero export document loader (enhanced for citation index).

Loads Better BibTeX JSON or BibTeX exports with citation indexing.
"""

from pathlib import Path
from typing import List, Dict, Any
from ..zotero import parse_zotero_export, CitationIndex
from .base import BaseDocLoader


class ZoteroDocLoader(BaseDocLoader):
    """Load Zotero exports with citation indexing."""
    
    def load(self, path: str, confidentiality: str = "internal") -> List[Dict[str, Any]]:
        """
        Load Zotero export and create chunks from bibliography.
        
        Args:
            path: Path to Zotero export (Better BibTeX JSON or .bib)
            confidentiality: Confidentiality level for chunks
            
        Returns:
            List of bibliography chunks with metadata
            
        Raises:
            FileNotFoundError: If export not found
            ValueError: If export invalid
        """
        try:
            items = parse_zotero_export(path)
        except Exception as e:
            raise ValueError(f"Failed to parse Zotero export: {e}")
        
        chunks = []
        
        for item in items:
            # Create content from item metadata
            content = f"""Title: {item.title}
Authors: {item.author_string()}
Year: {item.year or 'n.d.'}
Type: {item.item_type}
DOI: {item.doi or 'N/A'}
Citekey: {item.citekey}

Abstract:
{item.abstract or 'No abstract available.'}
"""
            
            chunk = self._create_chunk(
                content=content,
                source_path=str(path),
                doc_type='zotero',
                page_or_section=f"{item.citekey}: {item.title}",
                confidentiality=confidentiality,
                # Store Zotero metadata
                zotero_citekey=item.citekey,
                zotero_title=item.title,
                zotero_authors=item.author_string(),
                zotero_year=item.year,
                zotero_doi=item.doi or '',
                zotero_item_type=item.item_type
            )
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def create_citation_index(zotero_paths: List[str]) -> CitationIndex:
        """
        Create citation index from Zotero export files.
        
        Args:
            zotero_paths: List of paths to Zotero exports
            
        Returns:
            Populated CitationIndex
            
        Raises:
            ValueError: If any export invalid
        """
        index = CitationIndex()
        
        for path in zotero_paths:
            try:
                items = parse_zotero_export(path)
                index.add_items(items)
            except Exception as e:
                print(f"Warning: Failed to load Zotero export {path}: {e}")
        
        return index