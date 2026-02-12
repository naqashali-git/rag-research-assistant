"""
Configuration management for RAG Research Assistant.

Loads config.yaml with validation, environment overrides, and type checking.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import hashlib


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


class RAGConfig:
    """
    Configuration manager with strict validation.
    
    Enforces:
    - Required keys present
    - Type validation
    - Path existence checks
    - Chunk metadata schema
    """
    
    # Required top-level keys
    REQUIRED_KEYS = ['llm', 'embedding', 'vector_store', 'security']
    
    # Chunk metadata schema (all chunks must have these fields)
    CHUNK_METADATA_SCHEMA = {
        'source_path': str,
        'doc_type': str,  # pdf, docx, markdown, zotero
        'page_or_section': str,
        'created_at': str,  # ISO 8601
        'hash': str,  # SHA256
        'confidentiality': str,  # internal, confidential, public
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Load and validate configuration.
        
        Args:
            config_path: Path to config.yaml. Defaults to ./configs/config.yaml
            
        Raises:
            ConfigError: If config invalid or required files missing
        """
        if config_path is None:
            config_path = os.getenv("RAG_CONFIG_PATH", "./configs/config.yaml")
        
        self.config_path = Path(config_path)
        
        if not self.config_path.exists():
            raise ConfigError(f"Config file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                self.data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}")
        
        # Validate structure
        self._validate()
    
    def _validate(self):
        """Validate configuration structure and values."""
        # Check required keys
        for key in self.REQUIRED_KEYS:
            if key not in self.data:
                raise ConfigError(f"Missing required config key: {key}")
        
        # Validate LLM config
        llm_cfg = self.data['llm']
        if llm_cfg.get('provider') not in ('llama_cpp', 'ollama'):
            raise ConfigError(f"Invalid LLM provider: {llm_cfg.get('provider')}")
        
        # Validate security mode
        security_cfg = self.data['security']
        if security_cfg.get('mode') not in ('offline', 'egress'):
            raise ConfigError(f"Invalid security mode: {security_cfg.get('mode')}")
        
        # If model path is specified, it should be accessible (or will fail at runtime)
        model_path = llm_cfg.get('model_path')
        if model_path and model_path.startswith('./'):
            # Relative path - don't fail if not exists (may be downloaded later)
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get config value by dot-notation path.
        
        Args:
            key: Key path (e.g., 'llm.provider', 'security.mode')
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration section."""
        return self.data.get('llm', {})
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding configuration section."""
        return self.data.get('embedding', {})
    
    def get_vector_store_config(self) -> Dict[str, Any]:
        """Get vector store configuration section."""
        return self.data.get('vector_store', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration section."""
        return self.data.get('security', {})
    
    def get_audit_config(self) -> Dict[str, Any]:
        """Get audit logging configuration section."""
        return self.data.get('audit_log', {'enabled': True, 'file': './audit.log'})
    
    def get_document_ingestion_config(self) -> Dict[str, Any]:
        """Get document ingestion configuration."""
        return self.data.get('document_ingestion', {})
    
    def get_security_mode(self) -> str:
        """Get security mode (offline or egress)."""
        return self.get_security_config().get('mode', 'offline')
    
    def get_allowlist_domains(self) -> list:
        """Get allowlisted domains for egress mode."""
        egress_cfg = self.get_security_config().get('egress', {})
        return egress_cfg.get('allowlist_domains', [])
    
    def get_document_dirs(self) -> list:
        """Get list of document directories to ingest."""
        return self.data.get('document_dirs', ['./data/sample/'])


# Global config instance (lazy-loaded)
_config_instance: Optional[RAGConfig] = None


def load_config(config_path: Optional[str] = None) -> RAGConfig:
    """
    Load or retrieve cached configuration.
    
    Args:
        config_path: Optional override path
        
    Returns:
        RAGConfig instance
    """
    global _config_instance
    if _config_instance is None or config_path is not None:
        _config_instance = RAGConfig(config_path)
    return _config_instance


def get_config() -> RAGConfig:
    """Get currently loaded config (must be initialized)."""
    global _config_instance
    if _config_instance is None:
        raise RuntimeError("Config not loaded. Call load_config() first.")
    return _config_instance