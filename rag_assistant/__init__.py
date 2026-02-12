"""
RAG Research Assistant - Local-first, security-constrained research tool.

A fully offline, citation-grounded RAG system for engineering teams.
Supports PDF, DOCX, Markdown, and Zotero library ingestion.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from rag_assistant.config import RAGConfig, load_config
from rag_assistant.rag.engine import RAGEngine
from rag_assistant.loader import DocumentLoader

__all__ = ['RAGConfig', 'load_config', 'RAGEngine', 'DocumentLoader']
