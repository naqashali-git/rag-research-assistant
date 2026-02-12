"""Embedding generation using sentence-transformers."""

from typing import List
from sentence_transformers import SentenceTransformer


class EmbeddingManager:
    """Manages embeddings with sentence-transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding model.
        
        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed batch of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_single(self, text: str) -> List[float]:
        """
        Embed single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embedding = self.model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()


def get_embedding_manager(config: dict) -> EmbeddingManager:
    """Get configured embedding manager."""
    model_name = config.get('model', 'sentence-transformers/all-MiniLM-L6-v2')
    return EmbeddingManager(model_name)