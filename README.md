# RAG Research Assistant

**Local-first, security-constrained, citation-grounded RAG system for engineering teams.**

A production-ready research assistant that runs entirely offline by default, with optional controlled internet access. Ingests PDFs, DOCX, Markdown, and Zotero exports. Answers are grounded in retrieved documents with automatic citation generation in IEEE format.

## Features

✨ **Offline-First by Default**
- Runs entirely locally using `llama.cpp` or Ollama
- No external LLM API calls
- Full control over model and data

🔒 **Security & Compliance**
- Offline mode blocks all network sockets
- Egress mode: allowlist-only network access
- Query sanitization (no raw snippets leaked)
- Comprehensive audit logging of all network activity
- Zero response body logging (prevent exfiltration)
- Security self-test: `rag-assistant security self-test`

📚 **Multi-Format Document Support**
- PDF (via PyPDF2)
- DOCX/DOC (via python-docx)
- Markdown/TXT
- Zotero library exports (JSON)

📖 **Mandatory Metadata on All Chunks**
Every ingested chunk carries:
```
source_path    # Original file path
doc_type       # pdf, docx, markdown, zotero
page_or_section # Page number or heading
created_at     # ISO 8601 timestamp
hash           # SHA256 for chunk integrity
confidentiality # internal (default), confidential, public
```

💬 **Context-Only Answers**
The LLM is instructed:
> "Answer ONLY from provided context. If the context does not contain sufficient information, clearly state: 'I don't know based on the provided documents.'"

📚 **Citation-Grounded with Stable IDs**
- All answers cite retrieved documents using [n] notation
- Automatic IEEE-formatted bibliography generation
- Stable citation IDs for reproducibility

🔍 **Audit Everything**
- All queries logged (truncated to 200 chars)
- All network requests logged (URL, status, byte count, time)
- All model inference logged (input/output tokens, duration)
- Never logs response bodies (exfiltration prevention)

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/naqashali-git/rag-research-assistant.git
cd rag-research-assistant

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download a Model (Optional)

The default config expects a GGUF model file. Download one:

```bash
mkdir -p models
# Download llama-2-7b (3.5GB)
wget -O models/llama-2-7b-chat.ggmlv3.q4_0.bin \
  https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGML/resolve/main/llama-2-7b-chat.ggmlv3.q4_0.bin

# OR use Ollama instead (no download needed)
# ollama run llama2
```

### 3. Ingest Sample Documents

```bash
rag-assistant ingest --config configs/config.yaml --verbose
```

Sample documents in `data/sample/`:
- `meeting_sample.md` – Team meeting notes
- `zotero_export.json` – Bibliography with abstracts

### 4. Ask a Question

```bash
rag-assistant ask "What is RAG and why is it useful?"
```

Output:
```
======================================================================
ANSWER
======================================================================
RAG (Retrieval-Augmented Generation) is a technique that combines...

======================================================================
[BIBLIOGRAPHY]
[1] data/sample/meeting_sample.md (Discussion: RAG System Architecture)
[2] data/sample/zotero_export.json (Large Language Models...)
======================================================================
```

### 5. Verify Security

```bash
rag-assistant security self-test --config configs/config.yaml
```

Output:
```
======================================================================
SECURITY SELF-TEST RESULTS
======================================================================
Mode: offline

✓ [PASSED] test_offline_socket_blocked
        Network socket creation blocked in offline mode. Set security...

✓ [PASSED] test_offline_http_blocked
        Request blocked: SecurityViolation

✓ [PASSED] test_query_sanitization
        Query sanitized: search sensitive document content more secrets

✓ [PASSED] test_query_length_limit
        Query truncated to 100 chars

======================================================================
Summary: 4/4 tests passed
======================================================================
```

---

## Configuration

Main config: `configs/config.yaml`

### Offline Mode (Default - Recommended)

```yaml
security:
  mode: offline  # No network sockets allowed
```

### Egress Mode (Controlled Internet Access)

```yaml
security:
  mode: egress
  egress:
    enabled: true
    allowlist_domains:
      - "arxiv.org"
      - "ieeexplore.ieee.org"
    sanitize_queries: true
    max_query_length: 100
```

### Using Ollama Instead of llama.cpp

```yaml
llm:
  provider: ollama
  model: llama2
  base_url: http://localhost:11434
```

---

## CLI Commands

### `rag-assistant ask [QUERY]`

Ask a research question.

```bash
# Interactive prompt
rag-assistant ask

# Non-interactive
rag-assistant ask "What is machine learning?"

# Options
rag-assistant ask --query "..." --k 5 --output result.json
```

### `rag-assistant ingest`

Index documents from configured directories.

```bash
rag-assistant ingest --verbose
rag-assistant ingest --force-reindex
```

### `rag-assistant draft-ieee [OPTIONS]`

Generate IEEE LaTeX paper template.

```bash
rag-assistant draft-ieee --output my_paper.tex
```

### `rag-assistant security self-test`

Run security self-tests.

```bash
rag-assistant security self-test
```

### `rag-assistant audit-log [OPTIONS]`

View audit log.

```bash
rag-assistant audit-log
rag-assistant audit-log --follow
rag-assistant audit-log --lines 100
```

---

## Security & Threat Model

### Offline Mode (Default)

**Threat: Data exfiltration via HTTP/network calls**

**Mitigation:**
- `socket.socket` patched globally to raise `SecurityViolation`
- All network calls blocked at runtime
- Audit log records any attempted violations

**Self-test:** `security self-test` verifies socket creation is blocked

### Egress Mode (Controlled)

**Threat: Exfiltration through allowlisted domains**

**Mitigations:**
1. **Allowlist validation** - Only domains in config can be accessed
2. **Query sanitization** - Raw document snippets stripped before sending
   - Quotes ("...") removed
   - Special characters removed
   - Length limited (default 100 chars)
3. **Response sanitization** - Response bodies NEVER logged
4. **Audit trail** - Every request logged with URL, status, byte count

**Self-test:** `security self-test` verifies allowlist enforcement and query sanitization

### Audit Logging

All operations logged to `audit.log` as JSON for compliance:

```json
{
  "timestamp": "2024-01-15T10:23:45.123456",
  "event": "rag_query",
  "query": "What is machine learning? (truncated)",
  "num_results": 5,
  "execution_time_ms": 1523
}

{
  "timestamp": "2024-01-15T10:23:47.456789",
  "event": "network_egress",
  "method": "GET",
  "url": "https://arxiv.org/search?q=machine+learning",
  "status_code": 200,
  "response_size_bytes": 45230,
  "execution_time_ms": 1250
}
```

**Key guarantees:**
- ❌ Query text is truncated (200 chars)
- ❌ Response bodies are NEVER logged
- ✓ Network metadata is fully logged (URL, status, size, time)
- ✓ All model inference is logged (tokens, time)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ CLI (click)                                         │
├─────────────────────────────────────────────────────┤
│ ask | ingest | draft-ieee | security self-test     │
├─────────────────────────────────────────────────────┤
│ Config (YAML)                                       │
├──────────────────────────┬──────────────────────────┤
│ Document Loaders         │ Security (offline/egress)│
│ (PDF, DOCX, MD, Zotero)  │ + Self-test             │
├──────────────────────────┼──────────────────────────┤
│ Embedder (SentenceXForm) │ Audit Logger (JSON)     │
├──────────────────────────┤                          │
│ Vector Store (Chroma)    │                          │
├──────────────────────────┴──────────────────────────┤
│ RAG Engine (context-only answers)                   │
├─────────────────────────────────────────────────────┤
│ LLM (llama.cpp or Ollama - local inference)        │
└─────────────────────────────────────────────────────┘
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v --cov=rag_assistant
```

### Specific Test Suites

```bash
pytest tests/test_security.py -v  # Security tests
pytest tests/test_loaders.py -v   # Document loaders
pytest tests/test_end2end.py -v   # End-to-end
```

### GitHub Actions CI

- Lint (flake8)
- Unit tests (pytest)
- Security smoke test (offline mode + self-test)
- Document ingestion smoke test
- Sample query smoke test

---

## Development

### Project Structure

```
rag-research-assistant/
├── configs/config.yaml              # Main configuration
├── rag_assistant/
│   ├── cli.py                       # Click CLI commands
│   ├── config.py                    # Config management
│   ├── security.py                  # Security enforcement + self-test
│   ├── loader/                      # Document loaders (PDF, DOCX, MD, Zotero)
│   ├── retriever/                   # Embeddings + vector store
│   ├── rag/                         # RAG engine + citations
│   ├── llm/                         # Local LLM inference
│   └── audit/                       # Audit logging
├── tests/
│   ├── test_end2end.py             # Full pipeline tests
│   └── ...
├── data/sample/                     # Sample documents for demo
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

### Adding Custom Document Loaders

Extend `BaseDocLoader`:

```python
from rag_assistant.loader.base import BaseDocLoader

class MyDocLoader(BaseDocLoader):
    def load(self, path: str) -> List[Dict[str, Any]]:
        # Load documents
        chunks = [...]
        
        # Create chunks with mandatory metadata
        for content in chunks:
            return self._create_chunk(
                content=content,
                source_path=path,
                doc_type='my_format',
                page_or_section='...',
                confidentiality='internal'
            )
```

---

## Troubleshooting

### Model Not Found

```
FileNotFoundError: Failed to load model from ./models/llama-2.gguf
```

**Solution:** Download the model or update `configs/config.yaml` with correct path:

```bash
mkdir -p models
# Download or use Ollama instead
```

### Security Test Failures

```
✗ [FAILED] test_offline_socket_blocked
```

**Solution:** Socket patching may fail if already patched. Restart Python process.

### No Documents Indexed

```
⚠ No documents found in configured directories.
```

**Solution:** Add documents to directories listed in `configs/config.yaml`:

```yaml
document_dirs:
  - ./data/sample/
  - ./my_docs/
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit a pull request

**Code Standards:**
- PEP 8 (enforced by flake8)
- Comprehensive docstrings (Google style)
- Type hints on public APIs
- Unit tests for new features
- Audit tests for security-sensitive code

---

## License

MIT License – See LICENSE file

---

## Citation

If you use this tool in research, please cite:

```bibtex
@software{rag_research_assistant_2024,
  title={RAG Research Assistant},
  author={Your Team},
  year={2024},
  url={https://github.com/naqashali-git/rag-research-assistant}
}
```

---

## FAQ

**Q: Can I use this in production?**

A: The core components (loaders, RAG engine, security) are production-ready. The LLM inference depends on your model choice. Test thoroughly with your specific use case.

**Q: How do I handle sensitive documents?**

A: Mark them with confidentiality level:

```python
loader.load(path, confidentiality='confidential')
```

Audit logs respect this metadata.

**Q: Can I use this with my own LLM?**

A: Yes. Extend `rag_assistant.llm.llama_cpp.LlamaCppLLM` with your provider, or use Ollama.

**Q: How is security actually enforced?**

A: Multiple layers:
1. **Offline mode** patches `socket.socket` globally
2. **Egress mode** validates URLs against allowlist before any request
3. **Query sanitization** strips special characters and quotes
4. **Audit logging** records all attempts (blocked or allowed)
5. **Response sanitization** never logs response bodies

---

## Support

- **Documentation:** See `docs/` directory
- **Issues:** GitHub Issues
- **Security concerns:** Report privately to maintainers

---

**Built for engineering teams that care about data privacy and security.**