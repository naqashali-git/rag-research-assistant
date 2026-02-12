"""Local LLM inference using llama-cpp-python."""

from typing import Optional, Dict, Any
import time


class LlamaCppLLM:
    """Wrapper for llama-cpp-python local inference."""
    
    def __init__(self, model_path: str, context_length: int = 2048,
                 temperature: float = 0.7, max_tokens: int = 512):
        """
        Initialize Llama.cpp LLM.
        
        Args:
            model_path: Path to GGUF model file
            context_length: Context window size
            temperature: Sampling temperature
            max_tokens: Max output tokens
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("Install: pip install llama-cpp-python")
        
        self.model_path = model_path
        self.context_length = context_length
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        try:
            self.model = Llama(
                model_path=model_path,
                n_ctx=context_length,
                n_threads=-1,
                verbose=False
            )
        except Exception as e:
            raise FileNotFoundError(f"Failed to load model: {e}")
    
    def generate(self, prompt: str, max_tokens: Optional[int] = None,
                temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            
        Returns:
            Dict with 'text', 'tokens', 'time_ms'
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        start_time = time.time()
        
        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.95,
            stop=["Q:", "User:", "###"]
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            'text': response['choices'][0]['text'].strip(),
            'tokens': response['usage']['completion_tokens'],
            'time_ms': elapsed_ms
        }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.model.tokenize(text.encode('utf-8')))


def get_llm(config: dict) -> LlamaCppLLM:
    """Get configured LLM instance."""
    return LlamaCppLLM(
        model_path=config.get('model_path'),
        context_length=config.get('context_length', 2048),
        temperature=config.get('temperature', 0.7),
        max_tokens=config.get('max_tokens', 512)
    )