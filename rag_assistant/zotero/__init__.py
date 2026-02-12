"""
Zotero citation management module.

Supports:
- Better BibTeX JSON export (preferred)
- BibTeX (.bib) format
- Citation index (citekey, DOI, title)
- Bibliography generation (BibTeX and formatted)
"""

from .parser import parse_zotero_export, ZoteroItem
from .index import CitationIndex
from .formatter import BibTeXFormatter, FormattedCitationFormatter

__all__ = [
    'parse_zotero_export',
    'ZoteroItem',
    'CitationIndex',
    'BibTeXFormatter',
    'FormattedCitationFormatter',
]