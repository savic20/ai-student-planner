"""
LLM Package
-----------
Smart LLM integration with automatic fallback.

USAGE:
from app.llm import get_llm_gateway, LLMMessage, MessageRole

gateway = get_llm_gateway()
response = await gateway.generate("Hello, world!")
"""

from app.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse, MessageRole
from app.llm.groq_client import GroqClient
from app.llm.ollama_client import OllamaClient
from app.llm.gateway import LLMGateway, get_llm_gateway

__all__ = [
    # Base classes
    "BaseLLMClient",
    "LLMMessage",
    "LLMResponse",
    "MessageRole",
    
    # Clients
    "GroqClient",
    "OllamaClient",
    
    # Gateway
    "LLMGateway",
    "get_llm_gateway",
]