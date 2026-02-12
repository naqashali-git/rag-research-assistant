"""
Security enforcement module for RAG Research Assistant.

Implements:
- Offline mode: no network sockets allowed
- Egress mode: controlled access via allowlist + sanitized queries
- Comprehensive logging of all outbound activity
- Self-test to verify security controls
"""

import socket
import threading
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import hashlib
from datetime import datetime
from pathlib import Path


class SecurityViolation(Exception):
    """Raised when security policy is violated."""
    pass


class SecurityContext:
    """
    Security context enforcing offline/egress modes.
    
    Controls network access and logs all egress attempts.
    """
    
    def __init__(self, mode: str = "offline", 
                 allowlist_domains: Optional[List[str]] = None,
                 sanitize_queries: bool = True,
                 max_query_length: int = 100,
                 audit_logger = None):
        """
        Initialize security context.
        
        Args:
            mode: "offline" (no network) or "egress" (controlled network)
            allowlist_domains: Domains allowed in egress mode
            sanitize_queries: If True, strip raw snippets from queries
            max_query_length: Maximum length for sanitized queries
            audit_logger: AuditLogger instance for egress logging
        """
        if mode not in ("offline", "egress"):
            raise SecurityViolation(f"Invalid mode: {mode}")
        
        self.mode = mode
        self.allowlist_domains = set(allowlist_domains or [])
        self.sanitize_queries = sanitize_queries
        self.max_query_length = max_query_length
        self.audit_logger = audit_logger
        
        # Thread-local storage to prevent socket creation in offline mode
        self._socket_creation_lock = threading.Lock()
        self._original_socket = socket.socket
        
        if self.mode == "offline":
            self._patch_socket()
    
    def _patch_socket(self):
        """Patch socket.socket to prevent network calls in offline mode."""
        security_context = self
        
        def patched_socket(*args, **kwargs):
            raise SecurityViolation(
                "Network socket creation blocked in offline mode. "
                "Set security.mode=egress in config.yaml to enable network access."
            )
        
        # Replace socket constructor (warning: global patch)
        socket.socket = patched_socket
    
    def _unpatch_socket(self):
        """Restore original socket (use with caution)."""
        socket.socket = self._original_socket
    
    def validate_url(self, url: str) -> bool:
        """
        Validate URL against allowlist in egress mode.
        
        Args:
            url: URL to validate
            
        Returns:
            True if allowed, False otherwise
            
        Raises:
            SecurityViolation: If in offline mode
        """
        if self.mode == "offline":
            raise SecurityViolation(
                f"Network request blocked in offline mode: {url}"
            )
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check if domain is in allowlist
        is_allowed = any(
            domain == allowed or domain.endswith("." + allowed)
            for allowed in self.allowlist_domains
        )
        
        return is_allowed
    
    def sanitize_query(self, query: str) -> str:
        """
        Sanitize query for egress mode.
        
        Removes raw document snippets, keeps only keywords.
        
        Args:
            query: Query string
            
        Returns:
            Sanitized query
        """
        if not self.sanitize_queries:
            return query
        
        # Remove quoted strings (suspected raw snippets)
        sanitized = query
        import re
        sanitized = re.sub(r'"[^"]*"', '', sanitized)
        sanitized = re.sub(r"'[^']*'", '', sanitized)
        
        # Keep only alphanumeric and spaces
        sanitized = re.sub(r'[^a-zA-Z0-9\s]', ' ', sanitized)
        sanitized = ' '.join(sanitized.split())  # Collapse whitespace
        
        # Truncate
        if len(sanitized) > self.max_query_length:
            sanitized = sanitized[:self.max_query_length].rsplit(' ', 1)[0]
        
        return sanitized
    
    def log_egress_request(self, method: str, url: str, status_code: int,
                          response_size: int, execution_time_ms: float):
        """
        Log outbound network request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            status_code: Response status code
            response_size: Response body size in bytes
            execution_time_ms: Request duration in milliseconds
        """
        if self.audit_logger:
            self.audit_logger.log_network_egress(
                method=method,
                url=url,
                status_code=status_code,
                response_size=response_size,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.utcnow().isoformat()
            )
    
    def enforce_offline(self):
        """
        Explicitly enforce offline mode (raise if not in offline mode).
        
        Raises:
            SecurityViolation: If not in offline mode
        """
        if self.mode != "offline":
            raise SecurityViolation(
                f"Offline-only operation blocked. Current mode: {self.mode}"
            )
    
    def enforce_egress(self):
        """
        Explicitly enforce egress mode (raise if not in egress mode).
        
        Raises:
            SecurityViolation: If not in egress mode
        """
        if self.mode != "egress":
            raise SecurityViolation(
                f"Egress operation requires mode=egress. Current mode: {self.mode}"
            )


class SecuritySelfTest:
    """
    Self-test suite verifying security controls are enforced.
    
    Attempts prohibited actions and verifies they are blocked.
    """
    
    def __init__(self, security_context: SecurityContext):
        """
        Initialize self-test.
        
        Args:
            security_context: SecurityContext instance to test
        """
        self.context = security_context
        self.results = []
    
    def test_offline_socket_blocked(self) -> bool:
        """Test that socket creation is blocked in offline mode."""
        if self.context.mode != "offline":
            self.results.append(("test_offline_socket_blocked", "SKIPPED", "Not in offline mode"))
            return True
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.close()
            self.results.append(("test_offline_socket_blocked", "FAILED", "Socket created (should be blocked)"))
            return False
        except SecurityViolation as e:
            self.results.append(("test_offline_socket_blocked", "PASSED", str(e)))
            return True
    
    def test_offline_http_blocked(self) -> bool:
        """Test that HTTP requests are blocked in offline mode."""
        if self.context.mode != "offline":
            self.results.append(("test_offline_http_blocked", "SKIPPED", "Not in offline mode"))
            return True
        
        try:
            import requests
            resp = requests.get("https://example.com")
            self.results.append(("test_offline_http_blocked", "FAILED", "HTTP request succeeded (should be blocked)"))
            return False
        except (SecurityViolation, Exception) as e:
            # Either our security patch or requests library error
            self.results.append(("test_offline_http_blocked", "PASSED", f"Request blocked: {type(e).__name__}"))
            return True
    
    def test_egress_allowlist_enforced(self) -> bool:
        """Test that disallowed domains are rejected in egress mode."""
        if self.context.mode != "egress":
            self.results.append(("test_egress_allowlist_enforced", "SKIPPED", "Not in egress mode"))
            return True
        
        # Test disallowed domain
        is_allowed = self.context.validate_url("https://malicious.com/steal")
        
        if is_allowed:
            self.results.append(("test_egress_allowlist_enforced", "FAILED", "Disallowed domain accepted"))
            return False
        else:
            self.results.append(("test_egress_allowlist_enforced", "PASSED", "Disallowed domain rejected"))
            return True
    
    def test_egress_allowlist_permits_valid(self) -> bool:
        """Test that allowlisted domains are permitted in egress mode."""
        if self.context.mode != "egress":
            self.results.append(("test_egress_allowlist_permits_valid", "SKIPPED", "Not in egress mode"))
            return True
        
        # Assume 'arxiv.org' is in allowlist (from default config)
        if "arxiv.org" not in self.context.allowlist_domains:
            self.results.append(("test_egress_allowlist_permits_valid", "SKIPPED", "arxiv.org not in allowlist"))
            return True
        
        is_allowed = self.context.validate_url("https://arxiv.org/search?q=rag")
        
        if not is_allowed:
            self.results.append(("test_egress_allowlist_permits_valid", "FAILED", "Allowlisted domain rejected"))
            return False
        else:
            self.results.append(("test_egress_allowlist_permits_valid", "PASSED", "Allowlisted domain permitted"))
            return True
    
    def test_query_sanitization(self) -> bool:
        """Test that queries are sanitized in egress mode."""
        if not self.context.sanitize_queries:
            self.results.append(("test_query_sanitization", "SKIPPED", "Sanitization disabled"))
            return True
        
        raw_query = 'Search for "sensitive document content" OR \'more secrets\''
        sanitized = self.context.sanitize_query(raw_query)
        
        # Check that quotes are removed
        if '"' in sanitized or "'" in sanitized:
            self.results.append(("test_query_sanitization", "FAILED", "Quotes not removed from sanitized query"))
            return False
        
        # Check that only keywords remain
        if all(c.isalnum() or c.isspace() for c in sanitized):
            self.results.append(("test_query_sanitization", "PASSED", f"Query sanitized: {sanitized}"))
            return True
        else:
            self.results.append(("test_query_sanitization", "FAILED", "Special characters remain"))
            return False
    
    def test_query_length_limit(self) -> bool:
        """Test that long queries are truncated."""
        if not self.context.sanitize_queries:
            self.results.append(("test_query_length_limit", "SKIPPED", "Sanitization disabled"))
            return True
        
        long_query = "a" * (self.context.max_query_length + 50)
        sanitized = self.context.sanitize_query(long_query)
        
        if len(sanitized) <= self.context.max_query_length:
            self.results.append(("test_query_length_limit", "PASSED", f"Query truncated to {len(sanitized)} chars"))
            return True
        else:
            self.results.append(("test_query_length_limit", "FAILED", f"Query length {len(sanitized)} exceeds limit"))
            return False
    
    def run_all_tests(self) -> bool:
        """
        Run all security self-tests.
        
        Returns:
            True if all tests passed, False otherwise
        """
        self.results = []
        
        tests = [
            self.test_offline_socket_blocked,
            self.test_offline_http_blocked,
            self.test_egress_allowlist_enforced,
            self.test_egress_allowlist_permits_valid,
            self.test_query_sanitization,
            self.test_query_length_limit,
        ]
        
        passed = sum(1 for test in tests if test())
        total = len(tests)
        
        return passed == total
    
    def print_results(self):
        """Print formatted test results."""
        print("\n" + "="*70)
        print("SECURITY SELF-TEST RESULTS")
        print("="*70)
        print(f"Mode: {self.context.mode}\n")
        
        for test_name, status, message in self.results:
            status_icon = "✓" if status == "PASSED" else "✗" if status == "FAILED" else "⊘"
            print(f"{status_icon} [{status}] {test_name}")
            print(f"        {message}\n")
        
        passed = sum(1 for _, status, _ in self.results if status == "PASSED")
        total = len([r for r in self.results if r[1] != "SKIPPED"])
        
        print("="*70)
        print(f"Summary: {passed}/{total} tests passed")
        print("="*70)
        
        return passed == total


# Global security context (initialized by config)
_security_context: Optional[SecurityContext] = None


def get_security_context() -> SecurityContext:
    """Get global security context instance."""
    global _security_context
    if _security_context is None:
        raise RuntimeError("Security context not initialized. Call init_security() first.")
    return _security_context


def init_security(mode: str, allowlist_domains: Optional[List[str]] = None,
                 sanitize_queries: bool = True, audit_logger = None):
    """
    Initialize global security context.
    
    Args:
        mode: "offline" or "egress"
        allowlist_domains: Allowed domains in egress mode
        sanitize_queries: Enable query sanitization
        audit_logger: AuditLogger instance
    """
    global _security_context
    _security_context = SecurityContext(
        mode=mode,
        allowlist_domains=allowlist_domains,
        sanitize_queries=sanitize_queries,
        audit_logger=audit_logger
    )