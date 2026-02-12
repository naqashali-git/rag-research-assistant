"""
Embedding generation.

Primary: sentence-transformers (optional).
Fallback: deterministic hash embeddings (always available).

Key requirements:
- No import-time hard dependency on sentence-transformers.
- Fallback must be deterministic and dimension-stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import hashlib
import logging
import math

logger = logging.getLogger(__name__)


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _hash_embedding(text: str, dim: int) -> List[float]:
    """
    Deterministic embedding based on SHA256.
    Produces a stable unit-length vector of size `dim`.
    """
    # Expand digest material deterministically
    out: List[float] = []
    counter = 0
    while len(out) < dim:
        h = hashlib.sha256(f"{counter}|{text}".encode("utf-8", errors="ignore")).digest()
        # Map bytes -> floats in [-1, 1]
        for b in h:
            out.append((b / 127.5) - 1.0)
            if len(out) >= dim:
                break
        counter += 1
    return _l2_normalize(out[:dim])


@dataclass
class EmbeddingConfig:
    model: str = "sentence-transformers/all-MiniLM-L6-v2"
    backend: str = "auto"  # "auto" | "sentence_transformers" | "hash"
    fallback_dim: int = 384  # MUST match your index dimension in practice


class EmbeddingManager:
    """
    Manages embeddings with optional sentence-transformers and deterministic fallback.
    """

    def __init__(self, cfg: EmbeddingConfig):
        self.cfg = cfg
        self._model = None  # SentenceTransformer instance if available
        self.embedding_dim: Optional[int] = None
        self.backend_active: str = "hash"  # default until proven otherwise

        if cfg.backend not in {"auto", "sentence_transformers", "hash"}:
            raise ValueError(f"Unknown embeddings backend: {cfg.backend}")

        if cfg.backend in {"auto", "sentence_transformers"}:
            self._try_init_sentence_transformers()

        if self._model is None:
            # Fallback
            self.embedding_dim = int(cfg.fallback_dim)
            self.backend_active = "hash"
            logger.warning(
                "Using deterministic hash embeddings fallback (dim=%s). "
                "Retrieval quality will be reduced. Configure embeddings.fallback_dim "
                "to match your vector store dimension.",
                self.embedding_dim,
            )

    def _try_init_sentence_transformers(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # lazy import
        except Exception as e:
            logger.info("sentence-transformers unavailable: %s", e)
            return

        try:
            self._model = SentenceTransformer(self.cfg.model)
            self.embedding_dim = int(self._model.get_sentence_embedding_dimension())
            self.backend_active = "sentence_transformers"
        except Exception as e:
            logger.info("Failed to initialize sentence-transformers model: %s", e)
            self._model = None
            self.embedding_dim = None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self._model is not None:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()

        dim = int(self.embedding_dim or self.cfg.fallback_dim)
        return [_hash_embedding(t, dim) for t in texts]

    def embed_single(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]


def get_embedding_manager(config: dict, *, expected_dim: Optional[int] = None) -> EmbeddingManager:
    """
    Create an EmbeddingManager from config dict.

    Pass expected_dim (e.g., existing vector store dimension) to prevent
    dimension mismatch when falling back.
    """
    embeddings_cfg = config.get("embeddings", config)  # supports either layout
    model_name = embeddings_cfg.get("model", "sentence-transformers/all-MiniLM-L6-v2")
    backend = embeddings_cfg.get("backend", "auto")
    fallback_dim = int(embeddings_cfg.get("fallback_dim", expected_dim or 384))

    cfg = EmbeddingConfig(model=model_name, backend=backend, fallback_dim=fallback_dim)
    mgr = EmbeddingManager(cfg)

    # If we know what dim the store expects, enforce it in fallback mode
    if expected_dim is not None and mgr.backend_active == "hash" and mgr.embedding_dim != expected_dim:
        mgr.embedding_dim = int(expected_dim)
        logger.warning("Adjusted fallback embedding dim to expected_dim=%s", expected_dim)

    return mgr
