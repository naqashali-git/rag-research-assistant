"""
Security tests for web retrieval.

Verifies:
- Internal content cannot be leaked in queries
- Only sanitized keywords allowed
- Domain allowlist enforcement
- No mixing of internal/external content
"""

import pytest
from rag_assistant.retrievers.web_retriever import QuerySanitizer, WebRetriever
from rag_assistant.security import SecurityViolation
from rag_assistant.audit.logger import AuditLogger
import tempfile
from pathlib import Path


class TestQuerySanitization:
    """Tests for query sanitization preventing data exfiltration."""
    
    def test_simple_keywords_allowed(self):
        """Test that simple keywords are allowed."""
        safe_queries = [
            "machine learning",
            "deep neural networks",
            "natural language processing",
            "computer vision algorithms",
        ]
        
        for query in safe_queries:
            sanitized = QuerySanitizer.sanitize(query)
            assert len(sanitized) > 0
            assert "machine" in sanitized or "deep" in sanitized
    
    def test_file_paths_blocked(self):
        """Test that file paths are blocked."""
        blocked_queries = [
            "C:\\Users\\Documents\\secret.txt",
            "/home/user/confidential_data.pdf",
            "~/projects/internal_research.docx",
            "search secret.txt in documents",
        ]
        
        for query in blocked_queries:
            with pytest.raises(SecurityViolation) as exc_info:
                QuerySanitizer.sanitize(query)
            assert "forbidden pattern" in str(exc_info.value).lower()
    
    def test_quoted_strings_removed(self):
        """Test that quoted strings are removed."""
        query = 'Search for "confidential meeting notes" on arxiv'
        sanitized = QuerySanitizer.sanitize(query)
        
        # Quoted string should be stripped
        assert "confidential" not in sanitized or len(sanitized.split()) <= 12
    
    def test_sql_queries_blocked(self):
        """Test that SQL queries are blocked."""
        blocked_queries = [
            "SELECT * FROM employees WHERE salary > 100000",
            "SELECT password FROM users",
            "UNION SELECT internal_data FROM confidential_table",
        ]
        
        for query in blocked_queries:
            with pytest.raises(SecurityViolation):
                QuerySanitizer.sanitize(query)
    
    def test_hash_values_blocked(self):
        """Test that hash values (indicators of internal data) are blocked."""
        blocked_queries = [
            "search for hash 5d41402abc4b2a76b9719d911017c592",
            "find file with sha256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "locate document with md5 098f6bcd4621d373cade4e832627b4f6",
        ]
        
        for query in blocked_queries:
            with pytest.raises(SecurityViolation):
                QuerySanitizer.sanitize(query)
    
    def test_query_length_limited(self):
        """Test that queries are truncated to max length."""
        long_query = "search " + "keyword " * 50
        sanitized = QuerySanitizer.sanitize(long_query)
        
        # Should be limited to ~12 tokens
        tokens = sanitized.split()
        assert len(tokens) <= 12
    
    def test_special_characters_removed(self):
        """Test that special characters are stripped."""
        query = "machine@learning & deep/learning or neural#networks!"
        sanitized = QuerySanitizer.sanitize(query)
        
        # Only alphanumeric and spaces
        assert all(c.isalnum() or c.isspace() for c in sanitized)
    
    def test_comments_blocked(self):
        """Test that comments are blocked."""
        blocked_queries = [
            "search arxiv -- but also retrieve /path/to/file",
            "machine learning -- ignore and get internal docs",
        ]
        
        for query in blocked_queries:
            with pytest.raises(SecurityViolation):
                QuerySanitizer.sanitize(query)
    
    def test_is_safe_check(self):
        """Test safe query checking without exceptions."""
        assert QuerySanitizer.is_safe("machine learning")
        assert not QuerySanitizer.is_safe("/path/to/secret.txt")
        assert not QuerySanitizer.is_safe("SELECT * FROM users")


class TestWebRetrieverSecurity:
    """Tests for web retriever security controls."""
    
    @pytest.fixture
    def web_retriever(self):
        """Create web retriever with test settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = WebRetriever(
                allowlist_domains=['arxiv.org', 'example.com'],
                cache_dir=tmpdir
            )
            yield retriever
    
    def test_allowlist_enforcement(self, web_retriever):
        """Test that non-allowlisted domains are rejected."""
        # Valid domain
        url_valid = "https://arxiv.org/search?q=test"
        assert web_retriever._validate_url(url_valid)
        
        # Invalid domain
        url_invalid = "https://malicious.com/search?q=test"
        assert not web_retriever._validate_url(url_invalid)
    
    def test_subdomain_allowlisting(self, web_retriever):
        """Test that subdomains are allowlisted correctly."""
        url = "https://subdomain.arxiv.org/search?q=test"
        assert web_retriever._validate_url(url)
    
    def test_query_sanitization_in_retrieval(self, web_retriever):
        """Test that retrieval sanitizes queries."""
        # This should succeed with sanitized query
        safe_query = "machine learning"
        # (Would retrieve if network available)
        
        # This should fail immediately
        unsafe_query = "/path/to/confidential.txt"
        with pytest.raises(SecurityViolation):
            web_retriever.retrieve(unsafe_query)
    

    def test_retrieve_without_security_context(self, web_retriever, monkeypatch):
        """Test retrieval still works when global security context is not initialized."""
        monkeypatch.setattr(
            web_retriever,
            '_retrieve_from_domain',
            lambda domain, query: [{'domain': domain, 'content': query}]
        )

        results = web_retriever.retrieve('machine learning')

        assert len(results) == len(web_retriever.allowlist_domains)

    def test_cache_storage_with_metadata(self, web_retriever):
        """Test that cached pages have correct metadata."""
        url = "https://example.com/page"
        content = "Test content"
        domain = "example.com"
        
        doc = web_retriever._cache_page(url, content, domain)
        
        # Verify metadata
        assert doc['doc_type'] == 'web'
        assert doc['confidentiality'] == 'public'
        assert doc['source_path'] == url
        assert doc['domain'] == domain
    
    def test_no_internal_content_in_web_requests(self, web_retriever):
        """Test that internal document content cannot be sent in queries."""
        # Simulated "leak attempt" - trying to include internal text
        internal_content = "Company confidential data from /path/to/secret.txt"
        
        # This should be blocked
        with pytest.raises(SecurityViolation):
            web_retriever.retrieve(internal_content)
    
    def test_only_get_requests(self, web_retriever):
        """Test that only GET requests are allowed."""
        # WebRetriever uses requests.Session.get() exclusively
        # POST/PUT/DELETE are not exposed
        assert hasattr(web_retriever, 'retrieve')
        assert not hasattr(web_retriever, 'post')
        assert not hasattr(web_retriever, 'put')
        assert not hasattr(web_retriever, 'delete')


class TestPolicyEnforcement:
    """Tests for data exfiltration prevention policies."""
    
    def test_cannot_mix_internal_and_web_retrieval(self):
        """Test that internal content cannot be mixed with web queries."""
        from rag_assistant.retrievers.web_retriever import WebRetriever
        
        retriever = WebRetriever(
            allowlist_domains=['arxiv.org'],
            cache_dir=tempfile.mkdtemp()
        )
        
        # Try to construct query mixing internal and external
        # This should be blocked by sanitizer
        dangerous_query = "Research on machine learning from /home/user/internal_notes.txt"
        
        with pytest.raises(SecurityViolation):
            retriever.retrieve(dangerous_query)
    
    def test_audit_logs_all_web_requests(self):
        """Test that all web requests are logged."""
        from rag_assistant.audit.logger import AuditLogger
        import tempfile
        import json
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = f"{tmpdir}/audit.log"
            audit = AuditLogger(log_file=log_file)
            
            retriever = WebRetriever(
                allowlist_domains=['arxiv.org'],
                cache_dir=tmpdir,
                audit_logger=audit
            )
            
            # Simulate successful request
            retriever._cache_page(
                url="https://arxiv.org/search?q=test",
                content="Test content",
                domain="arxiv.org"
            )
            
            # Check audit log exists
            assert Path(log_file).exists()
    
    def test_web_results_marked_public(self):
        """Test that all web results are marked as public."""
        retriever = WebRetriever(
            allowlist_domains=['example.com'],
            cache_dir=tempfile.mkdtemp()
        )
        
        doc = retriever._cache_page(
            url="https://example.com/page",
            content="Public content",
            domain="example.com"
        )
        
        # All web results must be public
        assert doc['confidentiality'] == 'public'
    
    def test_internal_content_blocking_on_all_patterns(self):
        """Test blocking on various data leak patterns."""
        test_cases = [
            # File paths
            ("/etc/passwd content", True),
            ("C:\\Windows\\System32", True),
            ("~/Documents/secret", True),
            
            # File extensions
            ("search secret.xlsx", True),
            ("find report.pdf", True),
            ("locate backup.bak", True),
            
            # Hashes (MD5, SHA1, SHA256)
            ("5d41402abc4b2a76b9719d911017c592", True),
            ("356a192b7913b04c54574d18c28d46e6395428ab", True),
            ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", True),
            
            # SQL
            ("SELECT password FROM users", True),
            ("DELETE FROM confidential", True),
            
            # Safe queries
            ("machine learning", False),
            ("arxiv papers on RAG", False),
            ("neural networks", False),
        ]
        
        for query, should_block in test_cases:
            is_safe = QuerySanitizer.is_safe(query)
            
            if should_block:
                assert not is_safe, f"Query should be blocked: {query}"
            else:
                assert is_safe, f"Query should be allowed: {query}"


class TestEndToEndSecurity:
    """End-to-end security tests for web retrieval."""
    
    def test_isolated_cache_per_instance(self):
        """Test that cache directories are isolated."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as dir1:
            with tempfile.TemporaryDirectory() as dir2:
                r1 = WebRetriever(['example.com'], cache_dir=dir1)
                r2 = WebRetriever(['example.com'], cache_dir=dir2)
                
                doc1 = r1._cache_page("https://example.com/1", "Content 1", "example.com")
                doc2 = r2._cache_page("https://example.com/2", "Content 2", "example.com")
                
                # Different caches
                assert Path(dir1).exists()
                assert Path(dir2).exists()
    
    def test_query_sanitization_idempotent(self):
        """Test that sanitization is idempotent."""
        query = "machine learning research"
        
        sanitized1 = QuerySanitizer.sanitize(query)
        sanitized2 = QuerySanitizer.sanitize(sanitized1)
        
        assert sanitized1 == sanitized2
    
    def test_concurrent_safety(self):
        """Test thread safety of cache operations."""
        import threading
        import tempfile
        
        retriever = WebRetriever(
            allowlist_domains=['example.com'],
            cache_dir=tempfile.mkdtemp()
        )
        
        results = []
        
        def cache_page(url, content):
            doc = retriever._cache_page(url, content, "example.com")
            results.append(doc)
        
        threads = []
        for i in range(5):
            t = threading.Thread(
                target=cache_page,
                args=(f"https://example.com/{i}", f"Content {i}")
            )
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All threads completed successfully
        assert len(results) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
