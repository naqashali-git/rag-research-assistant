"""
Parse Zotero export formats: Better BibTeX JSON and BibTeX (.bib).

Prefers Better BibTeX JSON if both are present.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import json
import re
from dataclasses import dataclass


@dataclass
class ZoteroItem:
    """Represents a single bibliographic item."""
    
    # Core identifiers
    key: str  # Zotero unique key
    citekey: str  # BibTeX citekey (from Better BibTeX or generated)
    doi: Optional[str] = None
    url: Optional[str] = None
    
    # Bibliographic data
    title: str = ""
    authors: List[str] = None  # List of author names
    year: Optional[int] = None
    item_type: str = ""  # article, book, inproceedings, etc.
    
    # Publication info
    journal: Optional[str] = None  # For articles
    booktitle: Optional[str] = None  # For conference papers
    publisher: Optional[str] = None  # For books
    
    # Additional fields
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    abstract: Optional[str] = None
    tags: List[str] = None
    
    # Raw BibTeX entry (if available)
    raw_bibtex: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.authors is None:
            self.authors = []
        if self.tags is None:
            self.tags = []
    
    def to_bibtex(self) -> str:
        """
        Convert to BibTeX entry format.
        
        Returns:
            BibTeX entry string
        """
        if self.raw_bibtex:
            return self.raw_bibtex
        
        lines = [f"@{self.item_type}{{{self.citekey},"]
        
        if self.title:
            lines.append(f'  title = {{{self.title}}},')
        
        if self.authors:
            authors_str = ' and '.join(self.authors)
            lines.append(f'  author = {{{authors_str}}},')
        
        if self.year:
            lines.append(f'  year = {{{self.year}}},')
        
        if self.journal:
            lines.append(f'  journal = {{{self.journal}}},')
        
        if self.booktitle:
            lines.append(f'  booktitle = {{{self.booktitle}}},')
        
        if self.publisher:
            lines.append(f'  publisher = {{{self.publisher}}},')
        
        if self.volume:
            lines.append(f'  volume = {{{self.volume}}},')
        
        if self.issue:
            lines.append(f'  issue = {{{self.issue}}},')
        
        if self.pages:
            lines.append(f'  pages = {{{self.pages}}},')
        
        if self.doi:
            lines.append(f'  doi = {{{self.doi}}},')
        
        if self.url:
            lines.append(f'  url = {{{self.url}}},')
        
        lines[-1] = lines[-1].rstrip(',')  # Remove trailing comma from last field
        lines.append("}")
        
        return '\n'.join(lines)
    
    def author_string(self) -> str:
        """Get formatted author string."""
        return ', '.join(self.authors) if self.authors else 'Unknown'
    
    def short_citation(self) -> str:
        """Get short citation (Author et al., Year)."""
        if not self.authors:
            return f"{self.title[:30]}... ({self.year or 'n.d.'})"
        
        first_author = self.authors[0].split(',')[0]  # Last name
        et_al = " et al." if len(self.authors) > 1 else ""
        return f"{first_author}{et_al} ({self.year or 'n.d.'})"


class BetterBibTeXParser:
    """Parse Better BibTeX JSON export format."""

    _ITEM_TYPE_MAP = {
        # CSL-JSON style types commonly emitted by Better BibTeX
        "journal-article": "article",
        "article-journal": "article",
        "paper-conference": "inproceedings",
        "chapter": "incollection",
        "webpage": "misc",
    }
    
    @staticmethod
    def parse(json_data: Union[str, dict]) -> List[ZoteroItem]:
        """
        Parse Better BibTeX JSON export.
        
        Args:
            json_data: JSON string or dict
            
        Returns:
            List of ZoteroItem objects
            
        Raises:
            ValueError: If JSON invalid
        """
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
        else:
            data = json_data
        
        items = []
        
        # Handle list of items
        if isinstance(data, list):
            items_list = data
        elif isinstance(data, dict) and 'items' in data:
            items_list = data['items']
        else:
            raise ValueError("Expected list of items or dict with 'items' key")
        
        for item_data in items_list:
            try:
                item = BetterBibTeXParser._parse_item(item_data)
                items.append(item)
            except Exception as e:
                print(f"Warning: Failed to parse item {item_data.get('key', 'unknown')}: {e}")
        
        return items
    
    @staticmethod
    def _parse_item(item_data: dict) -> ZoteroItem:
        """Parse single Better BibTeX item."""
        # Extract citekey (Better BibTeX uses 'citationKey')
        citekey = (
            item_data.get('citationKey') or
            item_data.get('key') or
            item_data.get('id', 'unknown')
        )
        
        # Parse authors
        authors = []
        if 'creators' in item_data:
            for creator in item_data['creators']:
                if isinstance(creator, dict):
                    name_parts = []
                    if creator.get('given'):
                        name_parts.append(creator['given'])
                    if creator.get('family'):
                        name_parts.append(creator['family'])
                    if name_parts:
                        authors.append(' '.join(name_parts))
                elif isinstance(creator, str):
                    authors.append(creator)
        
        # Parse year
        year = None
        if 'issued' in item_data:
            issued = item_data['issued']
            if isinstance(issued, dict) and 'date-parts' in issued:
                year_parts = issued['date-parts'][0] if issued['date-parts'] else None
                year = year_parts[0] if year_parts else None
            elif isinstance(issued, str):
                year_match = re.search(r'\b(20\d{2}|19\d{2})\b', issued)
                year = int(year_match.group(1)) if year_match else None
        
        raw_item_type = (item_data.get('type', 'misc') or 'misc').lower()
        item_type = BetterBibTeXParser._ITEM_TYPE_MAP.get(raw_item_type, raw_item_type)

        return ZoteroItem(
            key=item_data.get('key', ''),
            citekey=citekey,
            doi=item_data.get('DOI') or item_data.get('doi'),
            url=item_data.get('URL') or item_data.get('url'),
            title=item_data.get('title', ''),
            authors=authors,
            year=year,
            item_type=item_type,
            journal=item_data.get('publication') or item_data.get('journal'),
            booktitle=item_data.get('bookTitle') or item_data.get('booktitle'),
            publisher=item_data.get('publisher'),
            volume=item_data.get('volume'),
            issue=item_data.get('issue'),
            pages=item_data.get('pages'),
            abstract=item_data.get('abstract'),
            tags=[t.get('tag') for t in item_data.get('tags', []) if isinstance(t, dict) and 'tag' in t],
            raw_bibtex=item_data.get('raw_bibtex')
        )


class BibTeXFileParser:
    """Parse BibTeX (.bib) file format."""
    
    @staticmethod
    def parse(bib_content: str) -> List[ZoteroItem]:
        """
        Parse BibTeX file content.
        
        Args:
            bib_content: BibTeX file content as string
            
        Returns:
            List of ZoteroItem objects
            
        Raises:
            ValueError: If parsing fails
        """
        items = []
        
        # Find all @Type{citekey, ... } entries
        pattern = r'@(\w+)\s*{\s*([^,]+?)\s*,\s*(.*?)(?=@\w+\s*{|$)'
        
        for match in re.finditer(pattern, bib_content, re.IGNORECASE | re.DOTALL):
            try:
                item_type = match.group(1).lower()
                citekey = match.group(2).strip()
                fields_str = match.group(3)
                
                fields = BibTeXFileParser._parse_fields(fields_str)
                
                # Extract authors
                authors = []
                if 'author' in fields:
                    authors = BibTeXFileParser._parse_authors(fields['author'])
                
                # Extract year
                year = None
                if 'year' in fields:
                    year_str = fields['year'].strip('{}')
                    year_match = re.search(r'(20\d{2}|19\d{2})', year_str)
                    year = int(year_match.group(1)) if year_match else None
                
                item = ZoteroItem(
                    key=citekey,
                    citekey=citekey,
                    doi=fields.get('doi', '').strip('{}'),
                    url=fields.get('url', '').strip('{}'),
                    title=fields.get('title', '').strip('{}'),
                    authors=authors,
                    year=year,
                    item_type=item_type,
                    journal=fields.get('journal', '').strip('{}'),
                    booktitle=fields.get('booktitle', '').strip('{}'),
                    publisher=fields.get('publisher', '').strip('{}'),
                    volume=fields.get('volume', '').strip('{}'),
                    issue=fields.get('number', '').strip('{}'),
                    pages=fields.get('pages', '').strip('{}'),
                    abstract=fields.get('abstract', '').strip('{}'),
                    raw_bibtex=match.group(0)
                )
                items.append(item)
            
            except Exception as e:
                print(f"Warning: Failed to parse BibTeX entry: {e}")
        
        return items
    
    @staticmethod
    def _parse_fields(fields_str: str) -> Dict[str, str]:
        """Parse BibTeX field key-value pairs."""
        fields = {}
        
        # Match key = value patterns (handles nested braces)
        pattern = r'(\w+)\s*=\s*([{"].*?[}"]|[^,}]+)'
        
        for match in re.finditer(pattern, fields_str, re.IGNORECASE):
            key = match.group(1).lower()
            value = match.group(2).strip()
            fields[key] = value
        
        return fields
    
    @staticmethod
    def _parse_authors(author_str: str) -> List[str]:
        """Parse BibTeX author string (separated by 'and')."""
        author_str = author_str.strip('{}')
        authors = [a.strip() for a in author_str.split(' and ')]
        return authors


def parse_zotero_export(file_path: str, format_hint: Optional[str] = None) -> List[ZoteroItem]:
    """
    Parse Zotero export file (auto-detect format or use hint).
    
    Prefers Better BibTeX JSON if both formats present in directory.
    
    Args:
        file_path: Path to Zotero export file
        format_hint: Optional hint ('json', 'bibtex')
        
    Returns:
        List of ZoteroItem objects
        
    Raises:
        FileNotFoundError: If file not found
        ValueError: If format unsupported
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Zotero export not found: {file_path}")
    
    content = path.read_text(encoding='utf-8')
    
    # If directory given, prefer Better BibTeX JSON
    if path.is_dir():
        json_file = path / 'zotero.json'
        bib_file = path / 'bibliography.bib'
        
        if json_file.exists():
            return parse_zotero_export(str(json_file), format_hint='json')
        elif bib_file.exists():
            return parse_zotero_export(str(bib_file), format_hint='bibtex')
        else:
            raise FileNotFoundError(f"No Zotero export found in {file_path}")
    
    # Auto-detect format
    if format_hint is None:
        if path.suffix.lower() == '.json':
            format_hint = 'json'
        elif path.suffix.lower() == '.bib':
            format_hint = 'bibtex'
        else:
            # Try JSON first, fall back to BibTeX
            try:
                return BetterBibTeXParser.parse(content)
            except Exception:
                pass
    
    # Parse based on format
    if format_hint == 'json':
        return BetterBibTeXParser.parse(content)
    elif format_hint == 'bibtex':
        return BibTeXFileParser.parse(content)
    else:
        raise ValueError(f"Unsupported format: {format_hint}")
