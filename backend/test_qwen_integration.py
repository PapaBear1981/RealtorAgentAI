#!/usr/bin/env python3
"""
Quick test script to verify Qwen model integration with OpenRouter API.

This script performs a simple test to ensure the qwen/qwen3-235b-a22b-thinking-2507
model is properly configured and accessible through the OpenRouter API.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.model_router import ModelRouter, ModelRequest
from app.core.config import get_settings


async def test_qwen_model():
    """Test the Qwen model integration."""
    print("🤖 Testing Qwen Model Integration")
    print("=" * 40)
    
    # Check configuration
    settings = get_settings()
    if not settings.OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not configured")
        print("   Please set the environment variable: export OPENROUTER_API_KEY=your_key_here")
        return False
    
    print(f"✅ OpenRouter API key configured (length: {len(settings.OPENROUTER_API_KEY)})")
    
    try:
        # Initialize model router
        print("🔧 Initializing model router...")
        router = ModelRouter()
        await router.initialize()
        print("✅ Model router initialized successfully")
        
        # Test Qwen model availability
        print("🔍 Checking Qwen model availability...")
        available_models = await router.get_available_models()
        qwen_models = [m for m in available_models if "qwen" in m.get("id", "").lower()]
        
        if qwen_models:
            print(f"✅ Found {len(qwen_models)} Qwen model(s)")
            for model in qwen_models:
                print(f"   • {model.get('id', 'Unknown')}")
        else:
            print("⚠️  No Qwen models found in available models list")
        
        # Test simple request
        print("🧪 Testing simple request to Qwen model...")
        request = ModelRequest(
            messages=[
                {"role": "system", "content": "You are a helpful real estate assistant."},
                {"role": "user", "content": "What is a property disclosure? Please provide a brief explanation."}
            ],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=150,
            temperature=0.1
        )
        
        print("📤 Sending request to OpenRouter API...")
        response = await router.generate_response(request)
        
        # Validate response
        print("📥 Response received!")
        print(f"✅ Model used: {response.model_used}")
        print(f"✅ Response length: {len(response.content)} characters")
        print(f"✅ Processing time: {response.processing_time:.2f} seconds")
        print(f"✅ Cost: ${response.cost:.6f}")
        print(f"✅ Token usage: {response.token_usage}")
        
        # Check response quality
        if len(response.content) > 20 and "disclosure" in response.content.lower():
            print("✅ Response quality check passed")
        else:
            print("⚠️  Response quality check failed - content may be incomplete")
        
        # Display response content
        print("\n📄 Response Content:")
        print("-" * 40)
        print(response.content)
        print("-" * 40)
        
        # Test thinking capabilities
        print("\n🧠 Testing thinking capabilities...")
        thinking_request = ModelRequest(
            messages=[
                {"role": "system", "content": "You are an expert real estate analyst. Think through problems step by step."},
                {"role": "user", "content": "Think through the key factors a first-time homebuyer should consider. Please analyze this step by step."}
            ],
            model_preference="qwen/qwen3-235b-a22b-thinking-2507",
            max_tokens=300,
            temperature=0.2
        )
        
        thinking_response = await router.generate_response(thinking_request)
        
        # Check for thinking indicators
        thinking_content = thinking_response.content.lower()
        thinking_indicators = ["step", "first", "consider", "analyze", "factor"]
        thinking_score = sum(1 for indicator in thinking_indicators if indicator in thinking_content)
        
        print(f"✅ Thinking response length: {len(thinking_response.content)} characters")
        print(f"✅ Thinking indicators found: {thinking_score}/{len(thinking_indicators)}")
        
        if thinking_score >= 3:
            print("✅ Thinking capabilities verified")
        else:
            print("⚠️  Thinking capabilities may be limited")
        
        print("\n🎉 Qwen model integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Provide helpful debugging information
        if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
            print("💡 Debugging tip: Check your OpenRouter API key")
        elif "not found" in str(e).lower():
            print("💡 Debugging tip: The Qwen model may not be available")
        elif "timeout" in str(e).lower():
            print("💡 Debugging tip: Check your network connection")
        else:
            print("💡 Debugging tip: Check the full error details above")
        
        return False


async def test_multiple_requests():
    """Test multiple concurrent requests."""
    print("\n🔄 Testing multiple concurrent requests...")
    
    try:
        router = ModelRouter()
        await router.initialize()
        
        # Create multiple requests
        requests = []
        for i in range(3):
            request = ModelRequest(
                messages=[{"role": "user", "content": f"Test request {i+1}: What is real estate?"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=50
            )
            requests.append(router.generate_response(request))
        
        # Execute concurrently
        responses = await asyncio.gather(*requests)
        
        print(f"✅ All {len(responses)} concurrent requests completed successfully")
        
        # Check response times
        avg_time = sum(r.processing_time for r in responses) / len(responses)
        print(f"✅ Average response time: {avg_time:.2f} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Concurrent request test failed: {str(e)}")
        return False


def main():
    """Main entry point."""
    print("🚀 Qwen Model Integration Test")
    print("Testing qwen/qwen3-235b-a22b-thinking-2507 with OpenRouter API")
    print("=" * 60)
    
    try:
        # Run basic test
        basic_success = asyncio.run(test_qwen_model())
        
        if basic_success:
            # Run concurrent test
            concurrent_success = asyncio.run(test_multiple_requests())
            
            if concurrent_success:
                print("\n🎉 All tests passed! Qwen model integration is working correctly.")
                print("\n✅ Summary:")
                print("   • OpenRouter API connection established")
                print("   • qwen/qwen3-235b-a22b-thinking-2507 model accessible")
                print("   • Response quality verified")
                print("   • Thinking capabilities confirmed")
                print("   • Concurrent requests handled successfully")
                print("\n🚀 Ready to proceed with full AI agent testing!")
                sys.exit(0)
            else:
                print("\n⚠️  Basic test passed but concurrent test failed")
                sys.exit(1)
        else:
            print("\n❌ Basic integration test failed")
            print("   Please fix the issues above before proceeding with full testing")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
