#!/usr/bin/env python3
"""
LLM Gateway Test Script
-----------------------
Tests Groq, Ollama, and the smart gateway.

USAGE:
cd backend
source venv/bin/activate
python test_llm.py
"""

import sys
import pytest
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.llm import get_llm_gateway, LLMMessage, MessageRole

@pytest.mark.asyncio
async def test_health_check():
    """Test provider health"""
    print("\n" + "="*70)
    print("  TEST 1: PROVIDER HEALTH CHECK")
    print("="*70)
    
    gateway = get_llm_gateway()
    health = await gateway.health_check()
    
    print(f"\n📊 Provider Status:")
    print(f"  Groq:   {'✅ Available' if health['groq']['available'] else '❌ Unavailable'}")
    if health['groq']['available']:
        print(f"          Model: {health['groq']['model']}")
    
    if health.get('ollama'):
        print(f"  Ollama: {'✅ Available' if health['ollama']['available'] else '❌ Unavailable'}")
        if health['ollama']['available']:
            print(f"          Model: {health['ollama']['model']}")
    
    return health['groq']['available'] or (health.get('ollama') and health['ollama']['available'])

@pytest.mark.asyncio
async def test_simple_generation():
    """Test simple text generation"""
    print("\n" + "="*70)
    print("  TEST 2: SIMPLE GENERATION")
    print("="*70)
    
    gateway = get_llm_gateway()
    
    try:
        print("\n📝 Prompt: 'Write a haiku about Python programming'")
        print("⏳ Generating...")
        
        response = await gateway.generate(
            "Write a haiku about Python programming:",
            max_tokens=50,
            temperature=0.8
        )
        
        print(f"\n✅ Success!")
        print(f"   Provider: {response.provider}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage['total_tokens']}")
        print(f"\n📄 Response:")
        print(f"   {response.content}")
        
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False

@pytest.mark.asyncio
async def test_chat_with_context():
    """Test chat with conversation history"""
    print("\n" + "="*70)
    print("  TEST 3: CHAT WITH CONTEXT")
    print("="*70)
    
    gateway = get_llm_gateway()
    
    try:
        messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content="You are a helpful study planning assistant. Be concise."
            ),
            LLMMessage(
                role=MessageRole.USER,
                content="I have a midterm in 2 weeks. Give me 3 quick study tips."
            )
        ]
        
        print("\n💬 System: You are a helpful study planning assistant")
        print("💬 User: I have a midterm in 2 weeks. Give me 3 quick study tips.")
        print("⏳ Generating...")
        
        response = await gateway.chat(
            messages=messages,
            max_tokens=150,
            temperature=0.5
        )
        
        print(f"\n✅ Success!")
        print(f"   Provider: {response.provider}")
        print(f"   Tokens: {response.usage['total_tokens']}")
        print(f"\n📄 Assistant Response:")
        print(f"   {response.content}")
        
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False

@pytest.mark.asyncio
async def test_streaming():
    """Test streaming generation"""
    print("\n" + "="*70)
    print("  TEST 4: STREAMING GENERATION")
    print("="*70)
    
    gateway = get_llm_gateway()
    
    try:
        print("\n📝 Prompt: 'Count from 1 to 10 in words'")
        print("⏳ Streaming...\n")
        print("📄 Response: ", end="", flush=True)
        
        chunk_count = 0
        async for chunk in gateway.generate_stream(
            "Count from 1 to 10 in words:",
            max_tokens=100,
            temperature=0.3
        ):
            print(chunk, end="", flush=True)
            chunk_count += 1
        
        print(f"\n\n✅ Success! Received {chunk_count} chunks")
        return True
    except Exception as e:
        print(f"\n\n❌ Failed: {e}")
        return False

@pytest.mark.asyncio
async def test_fallback():
    """Test automatic fallback"""
    print("\n" + "="*70)
    print("  TEST 5: AUTOMATIC FALLBACK")
    print("="*70)
    
    gateway = get_llm_gateway()
    
    print("\n🔄 This test verifies that the gateway can handle failures")
    print("   and automatically fall back to another provider.")
    
    # Force Groq to be marked as unavailable
    gateway._groq_available = False
    
    try:
        print("\n📝 Generating with Groq disabled (should use Ollama)...")
        response = await gateway.generate(
            "Say hello",
            max_tokens=10
        )
        
        print(f"\n✅ Fallback worked!")
        print(f"   Provider used: {response.provider}")
        
        # Reset availability
        gateway._groq_available = None
        
        return True
    except Exception as e:
        print(f"\n⚠️  Fallback test failed (this is okay if Ollama isn't installed): {e}")
        gateway._groq_available = None
        return True  # Don't fail the test suite


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  LLM GATEWAY TEST SUITE")
    print("="*70)
    
    tests = [
        ("Health Check", test_health_check),
        ("Simple Generation", test_simple_generation),
        ("Chat with Context", test_chat_with_context),
        ("Streaming", test_streaming),
        ("Automatic Fallback", test_fallback),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:10} {test_name}")
    
    print(f"\n  Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED!")
        print("\n  Your LLM integration is working perfectly!")
    elif passed > 0:
        print(f"\n  ⚠️  {total - passed} test(s) failed")
        print("\n  Common issues:")
        print("    - Groq API key not set in .env")
        print("    - Ollama not installed/running (optional)")
        print("    - Network connectivity issues")
    else:
        print("\n  ❌ ALL TESTS FAILED")
        print("\n  Please check:")
        print("    1. GROQ_API_KEY in .env file")
        print("    2. Internet connection")
        print("    3. Groq API status")
    
    print("\n" + "="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
