"""
Extended RAG engine supporting optional web retrieval.
"""

from typing import Optional, Dict, Any, List, Tuple
import time

from rag_assistant.rag.engine import RAGEngine
from rag_assistant.retrievers.web_retriever import WebRetriever, QuerySanitizer
from rag_assistant.security import get_security_context
from rag_assistant.audit.logger import AuditLogger


class RAGEngineWithWeb(RAGEngine):
    """RAG engine with optional web retrieval support."""
    
    def __init__(self, config_dict: Dict[str, Any], web_retriever: Optional[WebRetriever] = None):
        """
        Initialize RAG engine with web support.
        
        Args:
            config_dict: Configuration dictionary
            web_retriever: Optional WebRetriever instance
        """
        super().__init__(config_dict)
        self.web_retriever = web_retriever
    
    def query_with_web(self, query_text: str, k: int = 5, 
                      use_web: bool = False) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Execute RAG query with optional web retrieval.
        
        Args:
            query_text: User query
            k: Number of local documents to retrieve
            use_web: Enable web retrieval
            
        Returns:
            Tuple of (answer, bibliography, retrieved_docs)
        """
        # Check if web retrieval is allowed
        if use_web and not self.web_retriever:
            raise ValueError("Web retrieval not configured")
        
        # Retrieve from local documents
        query_embedding = self.embedder.embed_single(query_text)
        retrieved_local = self.vector_store.search(query_embedding, k=k)
        
        # Optionally retrieve from web
        retrieved_web = []
        if use_web:
            try:
                # Sanitize query for web
                sanitized_query = QuerySanitizer.sanitize(query_text)
                retrieved_web = self.web_retriever.retrieve(sanitized_query, k=3)
            except Exception as e:
                if self.audit_logger:
                    self.audit_logger.log_error(
                        'web_retrieval_failed',
                        str(e),
                        {'query': query_text}
                    )
        
        # Combine results (local first, then web)
        all_retrieved = retrieved_local + retrieved_web
        
        # Generate answer using combined context
        return self._generate_answer_with_sources(query_text, all_retrieved)
    
    def _generate_answer_with_sources(self, query: str, 
                                     retrieved: List[Dict[str, Any]]) -> Tuple[str, str, List]:
        """Generate answer from combined local and web sources."""
        # Assemble context
        context_parts = []
        for i, doc in enumerate(retrieved, 1):
            source_type = f" [{doc['doc_type'].upper()}]" if doc.get('doc_type') else ""
            context_parts.append(
                f"[{i}]{source_type} {doc['source_path']} ({doc['page_or_section']}):\n{doc['content'][:400]}..."
            )
        context = "\n\n".join(context_parts)
        
        # Build prompt
        prompt = self._build_prompt(query, context)
        
        # Generate answer
        generation_start = time.time()
        result = self.llm.generate(prompt)
        generation_time = (time.time() - generation_start) * 1000
        
        # Format bibliography
        bibliography = self._format_mixed_bibliography(retrieved)
        
        # Log
        if self.audit_logger:
            self.audit_logger.log_query(
                query=query,
                num_results=len(retrieved),
                execution_time_ms=generation_time,
                local_results=len([r for r in retrieved if r.get('doc_type') != 'web']),
                web_results=len([r for r in retrieved if r.get('doc_type') == 'web'])
            )
        
        return result['text'], bibliography, retrieved
    
    def _format_mixed_bibliography(self, retrieved: List[Dict[str, Any]]) -> str:
        """Format bibliography with source type indicators."""
        lines = ["[BIBLIOGRAPHY]"]
        
        for i, doc in enumerate(retrieved, 1):
            source_type = doc.get('doc_type', 'unknown').upper()
            citation = f"[{i}] [{source_type}] {doc['source_path']} ({doc['page_or_section']})"
            lines.append(citation)
        
        return '\n'.join(lines)