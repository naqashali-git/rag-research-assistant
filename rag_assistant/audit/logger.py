"""
Audit logging for compliance and security.

Logs all operations with focus on network egress tracking.
No response bodies are logged (prevent exfiltration).
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    """
    Structured audit logger for security and compliance.
    
    Features:
    - JSON event logging
    - Network egress tracking (URL, status, byte count, time)
    - Never logs response bodies
    - Immutable append-only log file
    """
    
    def __init__(self, log_file: str = "./audit.log", level: str = "INFO"):
        """
        Initialize audit logger.
        
        Args:
            log_file: Path to audit log
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("rag_audit")
        self.logger.setLevel(getattr(logging, level))
        
        # File handler with JSON formatting
        fh = logging.FileHandler(self.log_file, mode='a')
        fh.setLevel(getattr(logging, level))
        
        # Plain formatter (each line is a JSON event)
        formatter = logging.Formatter('%(message)s')
        fh.setFormatter(formatter)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []
        self.logger.addHandler(fh)
    
    def _log_event(self, event_dict: Dict[str, Any]):
        """
        Log a structured event as JSON.
        
        Args:
            event_dict: Event data to log
        """
        event_dict['timestamp'] = datetime.utcnow().isoformat()
        self.logger.info(json.dumps(event_dict))
    
    def log_document_ingestion(self, source_path: str, doc_type: str, 
                              num_chunks: int, **kwargs):
        """
        Log document ingestion event.
        
        Args:
            source_path: Path to ingested document
            doc_type: Document type (pdf, docx, markdown, zotero)
            num_chunks: Number of chunks created
            **kwargs: Additional metadata
        """
        event = {
            "event": "document_ingestion",
            "source_path": source_path,
            "doc_type": doc_type,
            "num_chunks": num_chunks,
            **kwargs
        }
        self._log_event(event)
    
    def log_query(self, query: str, num_results: int, execution_time_ms: float, **kwargs):
        """
        Log RAG query execution.
        
        Args:
            query: User query (truncated for safety)
            num_results: Number of retrieved documents
            execution_time_ms: Query execution time
            **kwargs: Additional metadata
        """
        event = {
            "event": "rag_query",
            "query": query[:200],  # Truncate long queries
            "num_results": num_results,
            "execution_time_ms": execution_time_ms,
            **kwargs
        }
        self._log_event(event)
    
    def log_network_egress(self, method: str, url: str, status_code: int,
                          response_size: int, execution_time_ms: float, **kwargs):
        """
        Log outbound network request.
        
        IMPORTANT: Response body is NEVER logged (prevent exfiltration).
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            status_code: Response status code
            response_size: Response body size in bytes
            execution_time_ms: Request duration
            **kwargs: Additional metadata
        """
        event = {
            "event": "network_egress",
            "method": method,
            "url": url,
            "status_code": status_code,
            "response_size_bytes": response_size,
            "execution_time_ms": execution_time_ms,
            **kwargs
        }
        self._log_event(event)
    
    def log_security_violation(self, violation_type: str, details: str, **kwargs):
        """
        Log security violation attempt.
        
        Args:
            violation_type: Type of violation (offline_socket_attempt, etc.)
            details: Violation details
            **kwargs: Additional context
        """
        event = {
            "event": "security_violation",
            "violation_type": violation_type,
            "details": details,
            **kwargs
        }
        self._log_event(event)
    
    def log_model_inference(self, model_name: str, input_tokens: int,
                           output_tokens: int, inference_time_ms: float, **kwargs):
        """
        Log model inference event.
        
        Args:
            model_name: LLM model name/path
            input_tokens: Input token count
            output_tokens: Output token count
            inference_time_ms: Inference duration
            **kwargs: Additional metadata
        """
        event = {
            "event": "model_inference",
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "inference_time_ms": inference_time_ms,
            **kwargs
        }
        self._log_event(event)
    
    def log_error(self, error_type: str, message: str, context: Optional[Dict] = None):
        """
        Log system error.
        
        Args:
            error_type: Type of error
            message: Error message
            context: Optional context dictionary
        """
        event = {
            "event": "error",
            "error_type": error_type,
            "message": message,
            **(context or {})
        }
        self._log_event(event)


def get_audit_logger(config: Optional[Dict[str, Any]] = None) -> AuditLogger:
    """
    Get configured audit logger instance.
    
    Args:
        config: Audit config dict with 'file' and 'level' keys
        
    Returns:
        AuditLogger instance
    """
    if config is None:
        config = {'file': './audit.log', 'level': 'INFO'}
    
    return AuditLogger(
        log_file=config.get('file', './audit.log'),
        level=config.get('level', 'INFO')
    )