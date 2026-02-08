"""
Groq LLM Client
---------------
Implementation of BaseLLMClient for Groq API.

WHAT IS GROQ?
- Ultra-fast LLM inference (fastest in the market)
- Free tier available
- Supports Llama, Mixtral, Gemma models
- Perfect for production use

GROQ ADVANTAGES:
- Speed: 10x faster than other providers
- Cost: Free tier is generous
- Models: Access to latest open-source models
"""

import asyncio
from typing import List, AsyncIterator, Optional
import logging
from groq import AsyncGroq
from groq import RateLimitError, APIError

from app.llm.base_client import (
    BaseLLMClient, LLMMessage, LLMResponse, MessageRole
)
from app.config import settings

logger = logging.getLogger(__name__)


class GroqClient(BaseLLMClient):
    """
    Groq API client implementation.
    
    FEATURES:
    - Automatic retry on rate limits
    - Error handling
    - Token counting
    - Streaming support
    
    USAGE:
    client = GroqClient(model="llama-3.3-70b-versatile")
    response = await client.generate("Hello, world!")
    print(response.content)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize Groq client.
        
        ARGS:
        - api_key: Groq API key (defaults to settings.GROQ_API_KEY)
        - model: Model name (defaults to settings.GROQ_MODEL)
        - timeout: Request timeout
        - max_retries: Number of retry attempts
        """
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize Groq async client
        self.client = AsyncGroq(
            api_key=self.api_key,
            timeout=self.timeout
        )
        
        super().__init__(model=self.model, timeout=timeout)
        
        logger.info(f"Groq client initialized with model: {self.model}")
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from prompt.
        
        EXAMPLE:
        response = await groq_client.generate(
            "Explain quantum computing in simple terms:",
            max_tokens=200,
            temperature=0.3  # More focused/deterministic
        )
        """
        # Convert prompt to chat format (Groq uses chat API)
        messages = [
            LLMMessage(role=MessageRole.USER, content=prompt)
        ]
        
        return await self.chat(messages, max_tokens, temperature, **kwargs)
    
    async def chat(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Chat completion with retry logic.
        
        HANDLES:
        - Rate limit errors (retries with backoff)
        - API errors (logs and retries)
        - Network errors
        
        EXAMPLE:
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content="You are a study planner."),
            LLMMessage(role=MessageRole.USER, content="Help me plan my week."),
        ]
        response = await groq_client.chat(messages)
        """
        formatted_messages = self._format_messages(messages)
        
        for attempt in range(self.max_retries):
            try:
                # Call Groq API
                completion = await self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                # Extract response
                content = completion.choices[0].message.content
                
                # Build response object
                response = LLMResponse(
                    content=content,
                    model=self.model,
                    provider="groq",
                    usage={
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    },
                    metadata={
                        "finish_reason": completion.choices[0].finish_reason,
                        "model": completion.model
                    }
                )
                
                logger.info(
                    f"Groq request successful. "
                    f"Tokens: {response.usage['total_tokens']}, "
                    f"Model: {self.model}"
                )
                
                return response
            
            except RateLimitError as e:
                # Rate limit hit - wait and retry
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Groq rate limit hit. Retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Groq rate limit - max retries exceeded")
                    raise
            
            except APIError as e:
                # API error - log and retry
                logger.error(f"Groq API error: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise
            
            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected Groq error: {e}", exc_info=True)
                raise
    
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming generation.
        
        USAGE:
        async for chunk in groq_client.generate_stream("Write a story:"):
            print(chunk, end="", flush=True)
        """
        messages = [
            LLMMessage(role=MessageRole.USER, content=prompt)
        ]
        formatted_messages = self._format_messages(messages)
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,  # Enable streaming
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Groq streaming error: {e}", exc_info=True)
            raise
    
    async def is_available(self) -> bool:
        """
        Check if Groq API is available.
        
        RETURNS:
        True if Groq is reachable and working
        
        HOW IT WORKS:
        Sends a minimal test request to verify connectivity
        """
        try:
            # Send a minimal test request
            test_messages = [
                {"role": "user", "content": "test"}
            ]
            
            await self.client.chat.completions.create(
                model=self.model,
                messages=test_messages,
                max_tokens=5,
                timeout=5  # Quick timeout for health check
            )
            
            logger.info("✅ Groq API is available")
            return True
        
        except Exception as e:
            logger.warning(f"❌ Groq API unavailable: {e}")
            return False


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
async def example_usage():
    """Example of using GroqClient"""
    
    # Initialize client
    client = GroqClient()
    
    # Check if available
    if not await client.is_available():
        print("Groq is not available")
        return
    
    # Simple generation
    print("\n1. Simple generation:")
    response = await client.generate(
        "Write a haiku about coding:",
        max_tokens=50,
        temperature=0.8
    )
    print(f"Response: {response.content}")
    print(f"Tokens used: {response.usage['total_tokens']}")
    
    # Chat with context
    print("\n2. Chat with context:")
    messages = [
        LLMMessage(
            role=MessageRole.SYSTEM,
            content="You are a helpful study planning assistant."
        ),
        LLMMessage(
            role=MessageRole.USER,
            content="I have an exam in 2 weeks. Help me create a study schedule."
        )
    ]
    response = await client.chat(messages, max_tokens=200, temperature=0.5)
    print(f"Response: {response.content}")
    
    # Streaming
    print("\n3. Streaming generation:")
    async for chunk in client.generate_stream(
        "Tell me a short story about a robot:",
        max_tokens=100
    ):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())