"""
Web retrieval with strict security constraints.

Features:
- Allowlist-based domain validation
- Query sanitization (no internal text, keyword-only)
- Local caching of retrieved pages
- Audit logging of all requests
"""

import re
import hashlib
import json
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from datetime import datetime
import requests
from urllib.parse import urlparse, urlencode

from rag_assistant.security import SecurityViolation, get_security_context
from rag_assistant.retrievers import BaseRetriever
from rag_assistant.audit.logger import AuditLogger


class QuerySanitizer:
    """Sanitizes queries to prevent data exfiltration."""
    
    # Maximum tokens in query (approximately 1 token = 1.3 words)
    MAX_QUERY_LENGTH = 12
    
    # Forbidden patterns that indicate internal content
    FORBIDDEN_PATTERNS = [
        r'\.txt',  # File extensions
        r'\.pdf',
        r'\.docx',
        r'/path/to/',  # File paths
        r'C:\\',
        r'~/.*',
        r'\b[a-z0-9]{32}\b',  # Hash values (MD5-like)
        r'\b[a-z0-9]{40}\b',  # SHA1-like
        r'\b[a-z0-9]{64}\b',  # SHA256-like
        r'SELECT\s+.*FROM',  # SQL queries
        r'--\s*.*',  # Comments
    ]
    
    @staticmethod
    def sanitize(query: str) -> str:
        """
        Sanitize query for safe web retrieval.
        
        Removes:
        - File paths and extensions
        - Hash values
        - SQL queries
        - Special characters
        - Quoted strings (raw text)
        
        Args:
            query: Raw query from user
            
        Returns:
            Sanitized keyword query
            
        Raises:
            SecurityViolation: If query contains forbidden patterns
        """
        original_query = query
        
        # Check for forbidden patterns (BLOCK these)
        for pattern in QuerySanitizer.FORBIDDEN_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise SecurityViolation(
                    f"Query contains forbidden pattern: {pattern}. "
                    f"Queries must contain only simple keywords, not internal content."
                )
        
        # Remove quoted strings (e.g., "exact phrase")
        sanitized = re.sub(r'"[^"]*"', '', query)
        sanitized = re.sub(r"'[^']*'", '', sanitized)
        
        # Remove special characters except spaces and hyphens
        sanitized = re.sub(r'[^\w\s\-]', ' ', sanitized)
        
        # Collapse multiple spaces
        sanitized = ' '.join(sanitized.split())
        
        # Convert to lowercase
        sanitized = sanitized.lower()
        
        # Split into tokens and limit
        tokens = sanitized.split()
        if len(tokens) > QuerySanitizer.MAX_QUERY_LENGTH:
            tokens = tokens[:QuerySanitizer.MAX_QUERY_LENGTH]
        
        sanitized = ' '.join(tokens)
        
        if not sanitized or len(sanitized) < 3:
            raise SecurityViolation(
                f"Query too short after sanitization: '{sanitized}'. "
                f"Must contain at least 3 characters of searchable content."
            )
        
        return sanitized
    
    @staticmethod
    def is_safe(query: str) -> bool:
        """Check if query is safe without raising exception."""
        try:
            QuerySanitizer.sanitize(query)
            return True
        except SecurityViolation:
            return False


class WebRetriever(BaseRetriever):
    """
    Retrieve documents from allowlisted web domains.
    
    Security constraints:
    - Only GET requests
    - Allowlist validation
    - Query sanitization
    - Local caching
    - Audit logging
    """
    
    def __init__(self, allowlist_domains: List[str],
                 cache_dir: str = "./cache/web",
                 audit_logger: Optional[AuditLogger] = None,
                 timeout: int = 10):
        """
        Initialize web retriever.
        
        Args:
            allowlist_domains: List of allowed domain names
            cache_dir: Directory for caching retrieved pages
            audit_logger: Optional audit logger
            timeout: Request timeout in seconds
        """
        self.allowlist_domains = set(d.lower() for d in allowlist_domains)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.audit_logger = audit_logger
        self.timeout = timeout
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RAG-Research-Assistant/1.0 (+http://example.com/bot)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
    
    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve documents from web using sanitized query.
        
        Args:
            query: User query (will be sanitized)
            k: Number of results (unused, for interface compatibility)
            
        Returns:
            List of retrieved document dicts
            
        Raises:
            SecurityViolation: If query unsafe or domain not allowlisted
        """
        # Check security context
        security_context = get_security_context()
        if security_context.mode == "offline":
            raise SecurityViolation("Web retrieval disabled in offline mode")
        
        # Sanitize query
        sanitized_query = QuerySanitizer.sanitize(query)
        
        # Build search URLs for each domain
        results = []
        
        for domain in self.allowlist_domains:
            try:
                retrieved = self._retrieve_from_domain(domain, sanitized_query)
                results.extend(retrieved)
            except Exception as e:
                if self.audit_logger:
                    self.audit_logger.log_error(
                        'web_retrieval_error',
                        f"Failed to retrieve from {domain}: {e}",
                        {'domain': domain, 'query': sanitized_query}
                    )
        
        return results
    
    def _retrieve_from_domain(self, domain: str, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve documents from specific domain.
        
        Args:
            domain: Allowlisted domain
            query: Sanitized query
            
        Returns:
            List of document dicts
        """
        # Build domain-specific search URL
        url = self._build_search_url(domain, query)
        
        # Validate URL
        if not self._validate_url(url):
            raise SecurityViolation(f"URL not allowlisted: {url}")
        
        # Check cache first
        cached = self._get_cached_page(url)
        if cached:
            if self.audit_logger:
                self.audit_logger.log_event({
                    'event': 'web_retrieval_cached',
                    'domain': domain,
                    'query': query,
                    'url': url
                })
            return [cached]
        
        # Fetch from web
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Cache the response
            cached = self._cache_page(url, response.text, domain)
            
            if self.audit_logger:
                self.audit_logger.log_network_egress(
                    method='GET',
                    url=url,
                    status_code=response.status_code,
                    response_size=len(response.text),
                    execution_time_ms=response.elapsed.total_seconds() * 1000
                )
            
            return [cached]
        
        except requests.RequestException as e:
            raise Exception(f"Failed to retrieve {url}: {e}")
    
    def _build_search_url(self, domain: str, query: str) -> str:
        """Build search URL for domain."""
        domain_lower = domain.lower()
        
        # Domain-specific search endpoints
        if 'arxiv.org' in domain_lower:
            return f"https://arxiv.org/search/?query={urlencode({'query': query})}&searchtype=all&abstracts=show&order=-announced_date_first&size=25"
        elif 'scholar.google.com' in domain_lower:
            return f"https://scholar.google.com/scholar?q={urlencode({'q': query})}&hl=en"
        elif 'ieeexplore.ieee.org' in domain_lower:
            return f"https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={urlencode({'queryText': query})}"
        else:
            # Generic search endpoint
            return f"https://{domain}/search?q={urlencode({'q': query})}"
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL against allowlist."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check if domain matches allowlist
        for allowed_domain in self.allowlist_domains:
            if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                return True
        
        return False
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def _get_cached_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached page if exists."""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return None
    
    def _cache_page(self, url: str, content: str, domain: str) -> Dict[str, Any]:
        """Cache retrieved page and return as document."""
        cache_key = self._get_cache_key(url)
        
        doc = {
            'content': content[:2000],  # Limit cached content
            'source_path': url,
            'doc_type': 'web',
            'page_or_section': domain,
            'created_at': datetime.utcnow().isoformat(),
            'hash': hashlib.sha256(content.encode()).hexdigest(),
            'confidentiality': 'public',  # All web content is public
            'domain': domain,
            'cache_key': cache_key
        }
        
        # Save to cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(doc, f, indent=2)
        
        return doc
    
    def clear_cache(self):
        """Clear all cached pages."""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)