"""
LLM Gateway
-----------
Smart router that manages multiple LLM providers with automatic fallback.

WHAT THIS DOES:
1. Try Groq (fast, reliable)
2. If Groq fails → automatically try Ollama (local backup)
3. Track which provider is working
4. Log all requests for debugging

WHY THIS MATTERS:
- Resilience: App doesn't break if one provider is down
- Performance: Always use the fastest available provider
- Cost: Fall back to free local model when needed
- Development: Work offline with Ollama

ARCHITECTURE:
┌─────────────────────────────────────┐
│  Your Code                           │
│  gateway.generate("prompt")          │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│  LLM Gateway                         │
│  Tries: Groq → Ollama                │
└────────────┬────────────────────────┘
             │
      ┌──────┴──────┐
      ▼             ▼
   ┌────┐       ┌──────┐
   │Groq│       │Ollama│
   └────┘       └──────┘
"""

import asyncio
from typing import List, AsyncIterator, Optional
import logging

from app.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse
from app.llm.groq_client import GroqClient
from app.llm.ollama_client import OllamaClient
from app.config import settings

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Smart LLM gateway with automatic fallback.
    
    FEATURES:
    - Tries Groq first (fast)
    - Falls back to Ollama if Groq fails
    - Caches provider availability
    - Logs all requests
    - Thread-safe
    
    USAGE:
    gateway = LLMGateway()
    response = await gateway.generate("Hello, world!")
    # Automatically uses best available provider
    """
    
    def __init__(self):
        """
        Initialize gateway with Groq and Ollama clients.
        """
        self.groq_client = GroqClient()
        self.ollama_client = OllamaClient() if settings.LLM_FALLBACK_ENABLED else None
        
        # Cache provider availability (avoids repeated checks)
        self._groq_available: Optional[bool] = None
        self._ollama_available: Optional[bool] = None
        
        logger.info("LLM Gateway initialized")
        logger.info(f"  Groq: Enabled")
        logger.info(f"  Ollama fallback: {'Enabled' if self.ollama_client else 'Disabled'}")
    
    async def _check_provider_availability(self, force: bool = False):
        """
        Check which providers are available.
        
        ARGS:
        - force: Force recheck even if cached
        
        CACHING:
        Availability is cached to avoid slow health checks on every request.
        Set force=True to refresh cache.
        """
        if force or self._groq_available is None:
            logger.info("Checking Groq availability...")
            self._groq_available = await self.groq_client.is_available()
        
        if self.ollama_client and (force or self._ollama_available is None):
            logger.info("Checking Ollama availability...")
            self._ollama_available = await self.ollama_client.is_available()
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        prefer_groq: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using best available provider.
        
        STRATEGY:
        1. Try Groq (unless prefer_groq=False)
        2. If Groq fails, try Ollama
        3. If both fail, raise error
        
        ARGS:
        - prompt: The input prompt
        - max_tokens: Max tokens to generate
        - temperature: Creativity (0.0-1.0)
        - prefer_groq: Try Groq first (default: True)
        
        RETURNS:
        LLMResponse from whichever provider succeeded
        
        EXAMPLE:
        response = await gateway.generate(
            "Explain quantum computing:",
            max_tokens=200,
            temperature=0.5
        )
        print(f"Provider used: {response.provider}")
        """
        # Check availability (cached)
        await self._check_provider_availability()
        
        # Determine order of providers to try
        providers = []
        
        if prefer_groq and self._groq_available:
            providers.append(("Groq", self.groq_client))
        
        if self.ollama_client and self._ollama_available:
            providers.append(("Ollama", self.ollama_client))
        
        if prefer_groq and not self._groq_available and self._ollama_available:
            # Groq down but Ollama available
            providers.append(("Ollama", self.ollama_client))
        
        # Try each provider
        for provider_name, client in providers:
            try:
                logger.info(f"Attempting generation with {provider_name}...")
                
                response = await client.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                logger.info(f"✅ {provider_name} succeeded. Tokens: {response.usage.get('total_tokens', 0)}")
                return response
            
            except Exception as e:
                logger.warning(f"❌ {provider_name} failed: {e}")
                
                # Mark provider as unavailable
                if provider_name == "Groq":
                    self._groq_available = False
                elif provider_name == "Ollama":
                    self._ollama_available = False
                
                # Try next provider
                continue
        
        # All providers failed
        error_msg = "All LLM providers failed. Check Groq API key and Ollama installation."
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def chat(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        prefer_groq: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Chat completion with automatic fallback.
        
        EXAMPLE:
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content="You are a study planner."),
            LLMMessage(role=MessageRole.USER, content="Plan my week."),
        ]
        response = await gateway.chat(messages)
        """
        await self._check_provider_availability()
        
        providers = []
        if prefer_groq and self._groq_available:
            providers.append(("Groq", self.groq_client))
        if self.ollama_client and self._ollama_available:
            providers.append(("Ollama", self.ollama_client))
        
        for provider_name, client in providers:
            try:
                logger.info(f"Attempting chat with {provider_name}...")
                response = await client.chat(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                logger.info(f"✅ {provider_name} chat succeeded")
                return response
            except Exception as e:
                logger.warning(f"❌ {provider_name} chat failed: {e}")
                continue
        
        raise Exception("All LLM providers failed for chat")
    
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        prefer_groq: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming generation with fallback.
        
        USAGE:
        async for chunk in gateway.generate_stream("Write a story:"):
            print(chunk, end="")
        """
        await self._check_provider_availability()
        
        # Try Groq first
        if prefer_groq and self._groq_available:
            try:
                logger.info("Streaming with Groq...")
                async for chunk in self.groq_client.generate_stream(
                    prompt, max_tokens, temperature, **kwargs
                ):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Groq streaming failed: {e}")
                self._groq_available = False
        
        # Fallback to Ollama
        if self.ollama_client and self._ollama_available:
            try:
                logger.info("Streaming with Ollama...")
                async for chunk in self.ollama_client.generate_stream(
                    prompt, max_tokens, temperature, **kwargs
                ):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Ollama streaming failed: {e}")
                self._ollama_available = False
        
        raise Exception("All providers failed for streaming")
    
    async def health_check(self) -> dict:
        """
        Check health of all providers.
        
        RETURNS:
        {
            "groq": {"available": True, "model": "llama-3.3-70b-versatile"},
            "ollama": {"available": False, "error": "Connection refused"}
        }
        
        USAGE:
        health = await gateway.health_check()
        if not health["groq"]["available"]:
            alert_admin()
        """
        await self._check_provider_availability(force=True)
        
        return {
            "groq": {
                "available": self._groq_available,
                "model": self.groq_client.model if self._groq_available else None
            },
            "ollama": {
                "available": self._ollama_available,
                "model": self.ollama_client.model if self._ollama_available and self.ollama_client else None
            } if self.ollama_client else None
        }


# =============================================================================
# GLOBAL GATEWAY INSTANCE
# =============================================================================
# Create a single global instance to reuse across the app
_gateway: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    """
    Get the global LLM gateway instance.
    
    USAGE:
    from app.llm.gateway import get_llm_gateway
    
    gateway = get_llm_gateway()
    response = await gateway.generate("Hello!")
    """
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
async def example_usage():
    """Example of using the LLM Gateway"""
    
    gateway = get_llm_gateway()
    
    # Health check
    print("Checking provider health...")
    health = await gateway.health_check()
    print(f"Groq: {'✅' if health['groq']['available'] else '❌'}")
    if health['ollama']:
        print(f"Ollama: {'✅' if health['ollama']['available'] else '❌'}")
    print()
    
    # Simple generation
    print("1. Simple generation:")
    response = await gateway.generate(
        "Write a haiku about AI:",
        max_tokens=50,
        temperature=0.8
    )
    print(f"Provider: {response.provider}")
    print(f"Response: {response.content}")
    print(f"Tokens: {response.usage['total_tokens']}")
    
    # Streaming
    print("\n2. Streaming:")
    async for chunk in gateway.generate_stream(
        "Count from 1 to 5:",
        max_tokens=30
    ):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(example_usage())