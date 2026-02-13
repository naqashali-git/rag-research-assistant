"""RAG Research Assistant package exports."""

__version__ = "1.0.0"
__author__ = "Your Name"

from rag_assistant.config import RAGConfig, load_config
from rag_assistant.loader import DocumentLoader
from rag_assistant.rag.engine import RAGEngine

__all__ = ["RAGConfig", "load_config", "RAGEngine", "DocumentLoader"]
