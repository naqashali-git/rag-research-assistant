"""Embedding generation utilities with graceful fallback when optional deps are unavailable."""

from __future__ import annotations

import hashlib
import logging
from typing import Callable, List

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manage text embeddings with optional sentence-transformers backend."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._fallback_dim = 64

        try:
            sentence_transformer_cls = self._load_sentence_transformer()
            self._model = sentence_transformer_cls(model_name)
            self.embedding_dim = self._model.get_sentence_embedding_dimension()
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            logger.warning(
                "Falling back to deterministic hash embeddings for model '%s': %s",
                model_name,
                exc,
            )
            self.embedding_dim = self._fallback_dim

    @staticmethod
    def _load_sentence_transformer() -> Callable:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer

    def _fallback_embed(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed_bytes = digest * ((self._fallback_dim // len(digest)) + 1)
        raw = seed_bytes[: self._fallback_dim]
        return [((byte / 255.0) * 2.0) - 1.0 for byte in raw]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts."""
        if self._model is not None:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        return [self._fallback_embed(text) for text in texts]

    def embed_single(self, text: str) -> List[float]:
        """Embed a single text."""
        if self._model is not None:
            embedding = self._model.encode([text], convert_to_numpy=True)
            return embedding[0].tolist()
        return self._fallback_embed(text)


def get_embedding_manager(config: dict) -> EmbeddingManager:
    """Get configured embedding manager."""
    model_name = config.get("model", "sentence-transformers/all-MiniLM-L6-v2")
    return EmbeddingManager(model_name)
