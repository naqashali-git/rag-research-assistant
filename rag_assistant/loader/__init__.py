"""Document loading with metadata schema enforcement."""

from pathlib import Path
from typing import List, Dict, Any
from .pdf import PDFDocLoader
from .docx import DOCXDocLoader
from .markdown import MarkdownDocLoader
from .zotero import ZoteroDocLoader


LOADER_MAP = {
    '.pdf': PDFDocLoader,
    '.docx': DOCXDocLoader,
    '.doc': DOCXDocLoader,
    '.md': MarkdownDocLoader,
    '.txt': MarkdownDocLoader,
    '.json': ZoteroDocLoader,
}


class DocumentLoader:
    """Unified document loader with auto-detection."""
    
    def __init__(self):
        """Initialize loaders."""
        self.loaders = {
            ext: loader_class() for ext, loader_class in LOADER_MAP.items()
        }
    
    def load(self, path: str, confidentiality: str = "internal") -> List[Dict[str, Any]]:
        """
        Load document by auto-detecting format.
        
        Args:
            path: Path to document file
            confidentiality: Default confidentiality level
            
        Returns:
            List of document chunks with complete metadata
            
        Raises:
            FileNotFoundError: If file not found
            ValueError: If format not supported
        """
        file_path = Path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        ext = file_path.suffix.lower()
        
        if ext not in self.loaders:
            raise ValueError(f"Unsupported format: {ext}")
        
        loader = self.loaders[ext]
        return loader.load(path, confidentiality=confidentiality)
    
    def load_directory(self, dir_path: str, confidentiality: str = "internal") -> List[Dict[str, Any]]:
        """
        Load all supported documents from directory recursively.
        
        Args:
            dir_path: Directory path
            confidentiality: Default confidentiality level
            
        Returns:
            Combined list of all chunks
        """
        dir_path = Path(dir_path)
        all_chunks = []
        
        for ext in self.loaders.keys():
            for file in dir_path.rglob(f"*{ext}"):
                try:
                    chunks = self.load(str(file), confidentiality=confidentiality)
                    all_chunks.extend(chunks)
                except Exception as e:
                    print(f"⚠ Warning: Failed to load {file}: {e}")
        
        return all_chunks


def load_documents(config_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Load all documents from configured directories.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        List of chunks with enforced metadata schema
    """
    loader = DocumentLoader()
    all_chunks = []
    
    ingestion_cfg = config_dict.get('document_ingestion', {})
    default_confidentiality = ingestion_cfg.get('default_confidentiality', 'internal')
    
    doc_dirs = config_dict.get('document_dirs', ['./data/sample/'])
    
    for doc_dir in doc_dirs:
        try:
            chunks = loader.load_directory(doc_dir, confidentiality=default_confidentiality)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"⚠ Warning: Failed to load directory {doc_dir}: {e}")
    
    return all_chunks