"""Tests for embedding fallback behavior."""

from rag_assistant.retriever.embedder import EmbeddingManager


def test_fallback_embeddings_are_deterministic(monkeypatch):
    """Fallback path should produce stable embeddings and expected dimensions."""

    def _raise_import_error():
        raise ImportError("simulated missing sentence_transformers")

    monkeypatch.setattr(EmbeddingManager, "_load_sentence_transformer", staticmethod(_raise_import_error))

    manager = EmbeddingManager("sentence-transformers/all-MiniLM-L6-v2")

    first = manager.embed_single("hello")
    second = manager.embed_single("hello")
    third = manager.embed_single("world")

    assert manager.embedding_dim == 64
    assert len(first) == 64
    assert first == second
    assert first != third


def test_embed_texts_uses_fallback_for_batches(monkeypatch):
    """Batch embedding should work in fallback mode."""

    def _raise_import_error():
        raise ImportError("simulated missing sentence_transformers")

    monkeypatch.setattr(EmbeddingManager, "_load_sentence_transformer", staticmethod(_raise_import_error))

    manager = EmbeddingManager()
    embeddings = manager.embed_texts(["a", "b", "c"])

    assert len(embeddings) == 3
    assert all(len(vector) == 64 for vector in embeddings)
