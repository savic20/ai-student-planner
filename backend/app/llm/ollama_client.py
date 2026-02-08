"""
Ollama LLM Client
-----------------
Implementation of BaseLLMClient for local Ollama.

WHAT IS OLLAMA?
- Run LLMs locally on your machine
- Privacy: No data sent to external servers
- Free: No API costs
- Offline: Works without internet

WHEN TO USE:
- Groq API is down
- Rate limits exceeded
- Privacy concerns
- Development without internet

SETUP:
1. Install Ollama: https://ollama.ai/download
2. Pull a model: ollama pull llama2
3. That's it! Ollama runs automatically
"""

import asyncio
from typing import List, AsyncIterator, Optional
import logging
import httpx

from app.llm.base_client import (
    BaseLLMClient, LLMMessage, LLMResponse, MessageRole
)
from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """
    Ollama local LLM client.
    
    FEATURES:
    - Local inference (no external API)
    - Free and unlimited
    - Privacy-preserving
    - Works offline
    
    LIMITATIONS:
    - Slower than Groq (depends on your hardware)
    - Requires local installation
    - Limited to models you've downloaded
    
    USAGE:
    client = OllamaClient(model="llama2")
    response = await client.generate("Hello!")
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60  # Longer timeout for local inference
    ):
        """
        Initialize Ollama client.
        
        ARGS:
        - base_url: Ollama server URL (default: http://localhost:11434)
        - model: Model name (default: llama2)
        - timeout: Request timeout (local is slower, so longer timeout)
        """
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip('/')
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout
        
        super().__init__(model=self.model, timeout=timeout)
        
        logger.info(f"Ollama client initialized: {self.base_url}, model: {self.model}")
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using Ollama.
        
        EXAMPLE:
        response = await ollama_client.generate(
            "Explain what a syllabus is:",
            max_tokens=150
        )
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Ollama generate API
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature
                        }
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Build response
                llm_response = LLMResponse(
                    content=data.get("response", ""),
                    model=self.model,
                    provider="ollama",
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    },
                    metadata={
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "eval_duration": data.get("eval_duration")
                    }
                )
                
                logger.info(
                    f"Ollama request successful. "
                    f"Tokens: {llm_response.usage['total_tokens']}, "
                    f"Duration: {data.get('total_duration', 0) / 1e9:.2f}s"
                )
                
                return llm_response
            
            except httpx.HTTPError as e:
                logger.error(f"Ollama HTTP error: {e}")
                raise
            except Exception as e:
                logger.error(f"Ollama unexpected error: {e}", exc_info=True)
                raise
    
    async def chat(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Chat completion using Ollama.
        
        NOTE: Ollama's chat API is newer, we use the generate API
        with a formatted prompt that includes conversation history.
        
        EXAMPLE:
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content="You are helpful."),
            LLMMessage(role=MessageRole.USER, content="Hello!"),
        ]
        response = await ollama_client.chat(messages)
        """
        # Convert chat messages to a single prompt
        # Format: System: {system}\nUser: {user}\nAssistant: 
        prompt_parts = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == MessageRole.USER:
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == MessageRole.ASSISTANT:
                prompt_parts.append(f"Assistant: {msg.content}")
        
        # Add prompt for assistant response
        prompt_parts.append("Assistant:")
        prompt = "\n".join(prompt_parts)
        
        # Use generate endpoint
        return await self.generate(prompt, max_tokens, temperature, **kwargs)
    
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming generation with Ollama.
        
        USAGE:
        async for chunk in ollama_client.generate_stream("Write a story:"):
            print(chunk, end="")
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature
                        }
                    }
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
            
            except Exception as e:
                logger.error(f"Ollama streaming error: {e}", exc_info=True)
                raise
    
    async def is_available(self) -> bool:
        """
        Check if Ollama is running and accessible.
        
        RETURNS:
        True if Ollama server is running
        
        HOW TO START OLLAMA:
        - Mac/Linux: Ollama runs automatically after installation
        - Windows: Run "ollama serve" in terminal
        - Docker: docker run -d -p 11434:11434 ollama/ollama
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Check if Ollama server is running
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    
                    # Check if our model is available
                    model_available = any(
                        m.get("name") == self.model for m in models
                    )
                    
                    if model_available:
                        logger.info(f"✅ Ollama is available with model: {self.model}")
                        return True
                    else:
                        logger.warning(
                            f"⚠️  Ollama is running but model '{self.model}' not found. "
                            f"Run: ollama pull {self.model}"
                        )
                        return False
                
                return False
        
        except Exception as e:
            logger.warning(f"❌ Ollama unavailable: {e}")
            return False


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
async def example_usage():
    """Example of using OllamaClient"""
    
    # Initialize client
    client = OllamaClient()
    
    # Check if available
    print("Checking Ollama availability...")
    if not await client.is_available():
        print("❌ Ollama is not available.")
        print("\nTo fix this:")
        print("1. Install Ollama: https://ollama.ai/download")
        print(f"2. Run: ollama pull {client.model}")
        print("3. Start Ollama server")
        return
    
    print("✅ Ollama is available!\n")
    
    # Simple generation
    print("1. Generating response...")
    response = await client.generate(
        "Write a short poem about programming:",
        max_tokens=100,
        temperature=0.8
    )
    print(f"Response: {response.content}")
    print(f"Tokens: {response.usage['total_tokens']}")
    
    # Streaming
    print("\n2. Streaming response:")
    async for chunk in client.generate_stream(
        "Count from 1 to 5:",
        max_tokens=50
    ):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())