## Zotero Citation Management

### Overview

The RAG Research Assistant includes comprehensive Zotero integration for managing bibliographies:

- **Better BibTeX JSON** (preferred) or **BibTeX (.bib)** file support
- **Citation index** for fast lookup by citekey, DOI, or title
- **Multiple citation formats**: IEEE numeric, APA, HTML, Markdown
- **BibTeX export** for LaTeX papers
- **Citation search CLI**: `rag-assistant cite search <query>`

### Quick Start

#### 1. Export from Zotero

In Zotero, select items and export as:
- **Better BibTeX JSON** (recommended): Right-click → Export → Better BibTeX
- **BibTeX (.bib)**: Right-click → Export → BibTeX

Place the file in `data/sample/` (or any document directory):
```bash
cp ~/Downloads/zotero_export.json data/sample/