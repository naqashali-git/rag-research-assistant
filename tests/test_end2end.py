"""End-to-end tests with sample data."""

import pytest
import tempfile
from pathlib import Path
from rag_assistant.config import RAGConfig
from rag_assistant.loader import DocumentLoader, load_documents
from rag_assistant.security import SecurityContext, SecuritySelfTest
from rag_assistant.audit.logger import get_audit_logger


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_config_dict(temp_dir):
    """Create test configuration."""
    return {
        'llm': {
            'provider': 'llama_cpp',
            'model_path': './models/llama-2-7b.ggmlv3.q4_0.bin',
            'context_length': 512,
            'temperature': 0.7,
            'max_tokens': 128
        },
        'embedding': {
            'model': 'sentence-transformers/all-MiniLM-L6-v2'
        },
        'vector_store': {
            'path': f'{temp_dir}/vectorstore'
        },
        'security': {
            'mode': 'offline'
        },
        'audit_log': {
            'file': f'{temp_dir}/audit.log'
        },
        'document_dirs': [f'{temp_dir}/docs']
    }


def test_document_loader_markdown():
    """Test markdown document loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        md_file = Path(tmpdir) / 'test.md'
        md_file.write_text("# Section 1\n\nThis is test content.")
        
        loader = DocumentLoader()
        docs = loader.load(str(md_file))
        
        assert len(docs) > 0
        assert 'content' in docs[0]
        assert 'metadata' in docs[0]
        
        # Check metadata schema
        metadata = docs[0]['metadata']
        assert 'source_path' in metadata
        assert 'doc_type' in metadata
        assert 'page_or_section' in metadata
        assert 'hash' in metadata
        assert metadata['confidentiality'] == 'internal'
        assert len(metadata['hash']) == 64  # SHA256


def test_security_offline_mode():
    """Test offline mode security."""
    context = SecurityContext(mode='offline')
    tester = SecuritySelfTest(context)
    
    # Socket should be blocked
    with pytest.raises(Exception):
        import socket
        socket.socket()


def test_security_egress_allowlist():
    """Test egress mode allowlist."""
    context = SecurityContext(
        mode='egress',
        allowlist_domains=['arxiv.org', 'example.com']
    )
    
    # Allowed domain
    assert context.validate_url('https://arxiv.org/search')
    
    # Disallowed domain
    assert not context.validate_url('https://malicious.com/steal')


def test_query_sanitization():
    """Test query sanitization for egress."""
    context = SecurityContext(
        mode='egress',
        sanitize_queries=True,
        max_query_length=50
    )
    
    raw_query = 'Search for "sensitive data" OR \'secret content\''
    sanitized = context.sanitize_query(raw_query)
    
    # Quotes should be removed
    assert '"' not in sanitized
    assert "'" not in sanitized
    
    # Length should be limited
    assert len(sanitized) <= 50


def test_embedding_generation():
    """Test embedding generation."""
    from rag_assistant.retriever.embedder import get_embedding_manager
    
    config = {'model': 'sentence-transformers/all-MiniLM-L6-v2'}
    embedder = get_embedding_manager(config)
    
    texts = ["Hello world", "Test content"]
    embeddings = embedder.embed_texts(texts)
    
    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0


def test_audit_logging(temp_dir):
    """Test audit logging."""
    log_file = f'{temp_dir}/test.log'
    audit = get_audit_logger({'file': log_file, 'level': 'INFO'})
    
    audit.log_query(
        query="Test query",
        num_results=5,
        execution_time_ms=100.5
    )
    
    log_path = Path(log_file)
    assert log_path.exists()
    
    content = log_path.read_text()
    assert 'rag_query' in content
    assert 'Test query' in content


def test_security_self_test():
    """Test security self-test suite."""
    context = SecurityContext(mode='offline')
    tester = SecuritySelfTest(context)
    
    # Run tests
    tester.run_all_tests()
    
    # Should have results
    assert len(tester.results) > 0
    
    # Check that socket test is present
    result_names = [r[0] for r in tester.results]
    assert 'test_offline_socket_blocked' in result_names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])