# Engineering Team Meeting - Q1 2024

## Discussion: RAG System Architecture

On January 15, 2024, the engineering team met to discuss implementing
a local-first RAG (Retrieval-Augmented Generation) system for research.

### Key Points Discussed

1. **Local Model Execution**: The system must run offline by default using
   llama.cpp or Ollama for inference. No external LLM API calls.

2. **Security Constraints**: All network requests must be allowlisted.
   Query sanitization required. Full audit logging of network activity.
   Response bodies must never be logged.

3. **Citation Grounding**: All answers must cite source documents with
   stable identifiers. IEEE-formatted bibliography generation.

4. **Document Support**: Support for PDF, DOCX, Markdown, and Zotero
   library exports with mandatory metadata on all chunks.

5. **Context-Only Answers**: LLM instructed to only answer from provided
   context. If information missing, must say "I don't know".

### Document Structure

Every ingested chunk must include:
- `source_path`: Original file path
- `doc_type`: pdf, docx, markdown, zotero
- `page_or_section`: Page number or section heading
- `created_at`: ISO 8601 timestamp
- `hash`: SHA256 hash for integrity
- `confidentiality`: internal, confidential, or public

### Action Items

- [x] Design vector store schema with Chroma
- [x] Implement document loaders for all formats
- [x] Build RAG engine with context-only instruction
- [x] Create security module (offline/egress modes)
- [x] Implement audit logging
- [x] Create CLI interface
- [x] Write comprehensive tests
- [x] Set up GitHub Actions CI/CD

### Next Steps

Security self-test verification: Run `rag-assistant security self-test`
to verify offline mode and allowlist enforcement.