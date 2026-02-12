"""Vector store using Chromadb with citation support."""

from typing import List, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings


class ChromaVectorStore:
    """Vector store with stable citation identifiers."""
    
    def __init__(self, persist_dir: str = "./vectorstore/db", 
                 collection_name: str = "documents"):
        """
        Initialize Chroma vector store.
        
        Args:
            persist_dir: Directory for persistent storage
            collection_name: Collection name
        """
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir,
            anonymized_telemetry=False,
        )
        
        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self._doc_id_map = {}  # Map: actual_id -> stable_citation_id
    
    def add_documents(self, chunks: List[Dict[str, Any]], 
                     embeddings: List[List[float]]) -> Dict[str, str]:
        """
        Add chunks with embeddings.
        
        Args:
            chunks: List of chunks (with metadata)
            embeddings: Corresponding embedding vectors
            
        Returns:
            Mapping of chunk index to stable citation ID
        """
        citation_ids = {}
        
        for i, chunk in enumerate(chunks):
            # Generate stable citation ID based on source + hash
            citation_id = self._generate_citation_id(chunk, i)
            citation_ids[i] = citation_id
            
            # Use citation ID as Chroma ID for stable retrieval
            self.collection.add(
                ids=[citation_id],
                embeddings=[embeddings[i]],
                documents=[chunk['content']],
                metadatas=[{
                    'source_path': chunk['metadata'].get('source_path', ''),
                    'doc_type': chunk['metadata'].get('doc_type', ''),
                    'page_or_section': chunk['metadata'].get('page_or_section', ''),
                    'hash': chunk['metadata'].get('hash', ''),
                    'confidentiality': chunk['metadata'].get('confidentiality', 'internal'),
                    'created_at': chunk['metadata'].get('created_at', ''),
                    **{k: str(v) for k, v in chunk['metadata'].items() 
                       if k not in ['source_path', 'doc_type', 'page_or_section', 'hash', 'confidentiality', 'created_at']}
                }]
            )
        
        return citation_ids
    
    def _generate_citation_id(self, chunk: Dict[str, Any], index: int) -> str:
        """
        Generate stable citation ID.
        
        Format: {doc_type}_{source_hash}_{page_or_section}_{chunk_index}
        
        Args:
            chunk: Chunk with metadata
            index: Chunk index
            
        Returns:
            Stable citation identifier
        """
        metadata = chunk['metadata']
        source_path = metadata.get('source_path', 'unknown')
        doc_type = metadata.get('doc_type', 'unknown')
        page_or_section = metadata.get('page_or_section', 'unknown').replace('/', '_').replace(' ', '_')
        
        # Create stable ID from components
        citation_id = f"{doc_type}_{page_or_section}_{index:04d}"
        return citation_id
    
    def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar chunks with citation info.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results
            
        Returns:
            List of results with citation IDs
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        documents = []
        for i in range(len(results['ids'][0])):
            citation_id = results['ids'][0][i]
            metadata = results['metadatas'][0][i]
            
            documents.append({
                'citation_id': citation_id,  # Stable identifier
                'content': results['documents'][0][i],
                'source_path': metadata.get('source_path', ''),
                'doc_type': metadata.get('doc_type', ''),
                'page_or_section': metadata.get('page_or_section', ''),
                'confidentiality': metadata.get('confidentiality', 'internal'),
                'distance': results['distances'][0][i] if results['distances'] else None,
                'metadata': metadata
            })
        
        return documents
    
    def persist(self):
        """Persist vector store to disk."""
        self.client.persist()


def get_vector_store(config: dict) -> ChromaVectorStore:
    """Get configured vector store."""
    persist_dir = config.get('path', './vectorstore/db')
    return ChromaVectorStore(persist_dir=persist_dir)