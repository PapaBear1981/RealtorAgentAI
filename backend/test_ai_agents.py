#!/usr/bin/env python3
"""
Test script for AI Agent System.

This script tests the AI agent system to verify that it's working properly
and not returning mock data.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.model_router import get_model_router, ModelRequest
from app.services.agent_orchestrator import get_agent_orchestrator, AgentRole


async def test_model_router():
    """Test the model router to ensure it can make real API calls."""
    print("🔧 Testing Model Router...")

    try:
        router = get_model_router()
        await router.initialize()

        # Test with a simple request
        request = ModelRequest(
            messages=[{"role": "user", "content": "Hello! Please respond with 'AI system is working' if you can understand this message."}],
            model_preference="openrouter/auto",
            max_tokens=50,
            temperature=0.1
        )

        response = await router.generate_response(request)

        print(f"✅ Model Router Response: {response.content}")
        print(f"   Model Used: {response.model_used}")
        print(f"   Provider: {response.provider.value}")
        print(f"   Cost: ${response.cost:.6f}")
        print(f"   Processing Time: {response.processing_time:.2f}s")

        return True

    except Exception as e:
        print(f"❌ Model Router Test Failed: {e}")
        return False


async def test_agent_creation():
    """Test agent creation and basic functionality."""
    print("\n🤖 Testing Agent Creation...")

    try:
        orchestrator = get_agent_orchestrator()

        # Test creating different types of agents
        agent_roles = [
            AgentRole.DATA_EXTRACTION,
            AgentRole.CONTRACT_GENERATOR,
            AgentRole.HELP_AGENT
        ]

        for role in agent_roles:
            agent = orchestrator.create_agent(role)
            print(f"✅ Created {role.value} agent: {agent.role}")

        return True

    except Exception as e:
        print(f"❌ Agent Creation Test Failed: {e}")
        return False


async def test_agent_execution():
    """Test actual agent execution with real AI calls."""
    print("\n🚀 Testing Agent Execution...")

    try:
        orchestrator = get_agent_orchestrator()

        # Create a simple task for the help agent
        from app.services.agent_orchestrator import WorkflowTask, TaskPriority
        from datetime import datetime

        task = WorkflowTask(
            id="test_task_001",
            description="Please explain what a real estate purchase agreement is and list 3 key components that should be included.",
            expected_output="A clear explanation of real estate purchase agreements with 3 key components listed",
            agent_role=AgentRole.HELP_AGENT,
            priority=TaskPriority.HIGH,
            context={},  # Empty dict for context
            dependencies=[],
            created_at=datetime.utcnow()
        )

        # Create workflow with single task
        workflow_id = await orchestrator.create_workflow(
            tasks=[task],
            workflow_id="test_workflow_001",
            user_id="test_user"
        )

        print(f"✅ Created workflow: {workflow_id}")

        # Execute the workflow
        result = await orchestrator.execute_workflow(workflow_id)

        print(f"✅ Workflow Status: {result.status.value}")
        print(f"   Execution Time: {result.execution_time:.2f}s")
        print(f"   Cost: ${result.cost:.6f}")

        if result.results and "output" in result.results:
            output = result.results["output"]
            print(f"   AI Response: {output[:200]}...")

            # Check if this looks like a real AI response (not mock data)
            if "real estate purchase agreement" in output.lower() and len(output) > 100:
                print("✅ Response appears to be real AI-generated content")
                return True
            else:
                print("⚠️  Response may be mock data or too short")
                return False
        else:
            print("❌ No output in workflow results")
            return False

    except Exception as e:
        print(f"❌ Agent Execution Test Failed: {e}")
        return False


async def check_environment():
    """Check environment configuration."""
    print("🔍 Checking Environment Configuration...")

    settings = get_settings()

    # Check API keys
    api_keys = {
        "OpenAI": settings.OPENAI_API_KEY,
        "Anthropic": settings.ANTHROPIC_API_KEY,
        "OpenRouter": settings.OPENROUTER_API_KEY
    }

    available_providers = []
    for provider, key in api_keys.items():
        if key:
            print(f"✅ {provider} API key configured")
            available_providers.append(provider)
        else:
            print(f"⚠️  {provider} API key not configured")

    if not available_providers:
        print("❌ No AI provider API keys configured!")
        print("   Please set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY")
        return False

    print(f"✅ {len(available_providers)} AI provider(s) configured: {', '.join(available_providers)}")
    return True


async def main():
    """Run all tests."""
    print("🧪 AI Agent System Test Suite")
    print("=" * 50)

    # Check environment first
    env_ok = await check_environment()
    if not env_ok:
        print("\n❌ Environment check failed. Please configure API keys.")
        return

    # Run tests
    tests = [
        ("Model Router", test_model_router),
        ("Agent Creation", test_agent_creation),
        ("Agent Execution", test_agent_execution)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! AI Agent system is working properly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration and logs.")


if __name__ == "__main__":
    asyncio.run(main())
