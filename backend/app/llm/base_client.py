"""
Base LLM Client
---------------
Abstract base class for all LLM providers (Groq, Ollama, etc.)

EXPLANATION FOR BEGINNERS:
- This is an "interface" or "contract"
- All LLM clients (Groq, Ollama) must implement these methods
- This allows us to swap between providers easily
- Python uses ABC (Abstract Base Class) for this

WHY THIS MATTERS:
Instead of:
    if provider == "groq":
        groq_response = groq.chat(...)
    elif provider == "ollama":
        ollama_response = ollama.generate(...)

We do:
    response = llm_client.generate(...)  # Works with any provider!
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# MESSAGE ROLE ENUM
# =============================================================================

class MessageRole(str, Enum):
    """Roles for chat messages"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


# =============================================================================
# DATA CLASSES FOR STRUCTURED RESPONSES
# =============================================================================

@dataclass
class LLMMessage:
    """
    A single chat message.
    
    EXAMPLE:
    message = LLMMessage(
        role=MessageRole.USER,
        content="Hello, how are you?"
    )
    """
    role: MessageRole
    content: str


@dataclass
class LLMResponse:
    """
    Response from LLM.
    
    FIELDS:
    - content: The generated text
    - model: Which model was used
    - provider: Which provider (groq, ollama)
    - usage: Token counts
    - metadata: Any extra info
    
    EXAMPLE:
    response = LLMResponse(
        content="I'm doing well, thank you!",
        model="llama-3.3-70b-versatile",
        provider="groq",
        usage={"prompt_tokens": 10, "completion_tokens": 8}
    )
    """
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.usage is None:
            self.usage = {}
        if self.metadata is None:
            self.metadata = {}


# =============================================================================
# BASE LLM CLIENT (ABSTRACT CLASS)
# =============================================================================

class BaseLLMClient(ABC):
    """
    Abstract base class for LLM providers.
    
    ALL LLM CLIENTS MUST IMPLEMENT:
    - generate() - Single completion
    - generate_stream() - Streaming completion
    - chat() - Chat completion
    - is_available() - Check if provider is working
    
    USAGE:
    class GroqClient(BaseLLMClient):
        def generate(self, prompt, **kwargs):
            # Implementation here
            pass
    """
    
    def __init__(self, model: str, timeout: int = 30):
        """
        Initialize LLM client.
        
        ARGS:
        - model: Model name (e.g., "llama-3.3-70b-versatile")
        - timeout: Request timeout in seconds
        """
        self.model = model
        self.timeout = timeout
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion from a prompt.
        
        ARGS:
        - prompt: The input prompt
        - max_tokens: Maximum tokens to generate
        - temperature: Randomness (0.0 = deterministic, 1.0 = creative)
        
        RETURNS:
        LLMResponse with the generated text
        
        EXAMPLE:
        response = await client.generate(
            "Write a haiku about Python:",
            max_tokens=50,
            temperature=0.8
        )
        print(response.content)
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming completion.
        
        WHY STREAMING?
        - Faster perceived response time
        - User sees output as it's generated
        - Better UX for long responses
        
        YIELDS:
        Chunks of text as they're generated
        
        EXAMPLE:
        async for chunk in client.generate_stream("Explain quantum computing:"):
            print(chunk, end="", flush=True)
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Chat completion with conversation history.
        
        ARGS:
        - messages: List of conversation messages
        
        EXAMPLE:
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            LLMMessage(role=MessageRole.USER, content="What is Python?"),
        ]
        response = await client.chat(messages)
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the LLM provider is available.
        
        RETURNS:
        True if provider is reachable and working
        
        USAGE:
        if await groq_client.is_available():
            response = await groq_client.generate(prompt)
        else:
            # Use fallback
            response = await ollama_client.generate(prompt)
        """
        pass
    
    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """
        Convert LLMMessage objects to API format.
        
        WHAT THIS DOES:
        [LLMMessage(role="user", content="Hi")] 
        → 
        [{"role": "user", "content": "Hi"}]
        
        This is a helper method used by child classes.
        """
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    print("""
    BASE LLM CLIENT USAGE:
    
    This is an abstract class. You don't use it directly.
    Instead, you create specific implementations:
    
    1. Create a Groq client:
        groq_client = GroqClient(model="llama-3.3-70b-versatile")
    
    2. Create an Ollama client:
        ollama_client = OllamaClient(model="llama2")
    
    3. Use them interchangeably:
        async def get_response(client: BaseLLMClient, prompt: str):
            return await client.generate(prompt)
        
        # Works with any provider!
        response = await get_response(groq_client, "Hello")
        response = await get_response(ollama_client, "Hello")
    
    This is the power of abstraction!
    """)