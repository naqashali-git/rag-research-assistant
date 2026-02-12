"""RAG engine with context-only answer enforcement."""

from typing import Tuple, List, Dict, Any
import time
from rag_assistant.retriever.vector_store import get_vector_store
from rag_assistant.retriever.embedder import get_embedding_manager
from rag_assistant.llm.llama_cpp import get_llm
from rag_assistant.rag.citation import CitationFormatter
from rag_assistant.audit.logger import get_audit_logger


class RAGEngine:
    """RAG with strict context-only answers."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize RAG engine."""
        self.config = config_dict
        self.vector_store = get_vector_store(config_dict.get('vector_store', {}))
        self.embedder = get_embedding_manager(config_dict.get('embedding', {}))
        self.llm = get_llm(config_dict.get('llm', {}))
        self.audit = get_audit_logger(config_dict.get('audit_log', {}))
        self.citation_formatter = CitationFormatter()
    
    def index_documents(self, chunks: List[Dict[str, Any]]):
        """Index chunks with metadata into vector store."""
        if not chunks:
            return
        
        contents = [chunk['content'] for chunk in chunks]
        embeddings = self.embedder.embed_texts(contents)
        self.vector_store.add_documents(chunks, embeddings)
        self.vector_store.persist()
        
        self.audit.log_document_ingestion(
            source_path="batch_ingestion",
            doc_type="mixed",
            num_chunks=len(chunks)
        )
    
    def query(self, query_text: str, k: int = 5) -> Tuple[str, str, List[Dict[str, Any]]]:
        """Execute RAG query with context-only instruction."""
        query_start = time.time()
        
        # Embed query
        query_embedding = self.embedder.embed_single(query_text)
        
        # Retrieve chunks
        retrieved = self.vector_store.search(query_embedding, k=k)
        
        # Assemble context with citations
        context_parts = []
        for i, doc in enumerate(retrieved, 1):
            context_parts.append(
                f"[{i}] {doc['source_path']} ({doc['page_or_section']}):\n{doc['content'][:400]}..."
            )
        context = "\n\n".join(context_parts)
        
        # Build prompt with context-only instruction
        prompt = self._build_prompt(query_text, context)
        
        # Generate answer
        generation_start = time.time()
        result = self.llm.generate(prompt)
        generation_time = (time.time() - generation_start) * 1000
        
        # Format bibliography
        bibliography = self.citation_formatter.format_bibliography(
            retrieved, 
            style=self.config.get('output', {}).get('citation_format', 'ieee')
        )
        
        # Log
        total_time = (time.time() - query_start) * 1000
        self.audit.log_query(
            query=query_text,
            num_results=len(retrieved),
            execution_time_ms=total_time
        )
        
        self.audit.log_model_inference(
            model_name=self.llm.model_path,
            input_tokens=self.llm.count_tokens(prompt),
            output_tokens=result['tokens'],
            inference_time_ms=generation_time
        )
        
        return result['text'], bibliography, retrieved
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Build prompt enforcing context-only answers."""
        system_prompt = self.config.get('llm', {}).get('system_prompt', 
            "Answer ONLY from provided context. If missing, say 'I don't know based on the provided documents.'"
        )
        
        return f"""{system_prompt}

QUESTION: {query}

CONTEXT:
{context}

ANSWER (cite with [n]):
"""