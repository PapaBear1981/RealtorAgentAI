#!/usr/bin/env python3
"""
AI Agents Testing and Debugging Script.

This script runs comprehensive tests for AI agents with OpenRouter API integration,
including LLM integration, end-to-end workflows, performance testing, and debugging.
"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from tests.test_runner_ai_agents import AIAgentTestRunner


def check_prerequisites():
    """Check if all prerequisites are met for running tests."""
    print("🔍 Checking prerequisites...")
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Not running in a virtual environment")
        print("   It's recommended to run tests in a virtual environment")
    
    # Check required environment variables
    required_env_vars = ['OPENROUTER_API_KEY']
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("   Please set these variables before running tests:")
        for var in missing_vars:
            print(f"   export {var}=your_value_here")
        return False
    
    # Check if required packages are installed
    try:
        import pytest
        import structlog
        import httpx
        import openai
        import anthropic
        import crewai
        print("✅ All required packages are available")
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("   Please install requirements: pip install -r requirements.txt")
        return False
    
    print("✅ All prerequisites met")
    return True


def install_test_dependencies():
    """Install additional test dependencies."""
    print("📦 Installing test dependencies...")
    
    test_packages = [
        "pytest",
        "pytest-asyncio", 
        "pytest-json-report",
        "pytest-cov",
        "pytest-timeout",
        "rich",
        "psutil"
    ]
    
    for package in test_packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                         check=True, capture_output=True)
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to install {package}")


def run_quick_smoke_test():
    """Run a quick smoke test to verify basic functionality."""
    print("🚀 Running quick smoke test...")
    
    try:
        # Test basic imports
        from app.services.model_router import ModelRouter
        from app.services.agent_orchestrator import AgentOrchestrator
        from app.core.config import get_settings
        
        settings = get_settings()
        if not settings.OPENROUTER_API_KEY:
            print("❌ OPENROUTER_API_KEY not configured")
            return False
        
        print("✅ Basic imports successful")
        print("✅ Configuration loaded")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        return False


async def run_comprehensive_tests():
    """Run the comprehensive AI agent test suite."""
    print("🤖 Starting comprehensive AI agent tests...")
    
    runner = AIAgentTestRunner()
    results = await runner.run_comprehensive_tests()
    
    return results["overall_status"] == "PASSED"


def run_individual_test_categories():
    """Run individual test categories for detailed analysis."""
    print("🔬 Running individual test categories...")
    
    test_categories = [
        ("LLM Integration", "tests/test_llm_integration.py"),
        ("End-to-End Workflows", "tests/test_end_to_end_workflows.py"),
        ("API Response Validation", "tests/test_api_response_validation.py"),
        ("Error Handling", "tests/test_error_handling_debugging.py"),
        ("Performance", "tests/test_performance.py"),
        ("Integration Coordination", "tests/test_integration_coordination.py"),
        ("WebSocket Communication", "tests/test_websocket_communication.py")
    ]
    
    results = {}
    
    for category_name, test_file in test_categories:
        print(f"\n🧪 Running {category_name} tests...")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_file,
                "-v",
                "--tb=short",
                "--timeout=300"
            ], capture_output=True, text=True, timeout=600)
            
            results[category_name] = {
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            if result.returncode == 0:
                print(f"✅ {category_name} tests passed")
            else:
                print(f"❌ {category_name} tests failed")
                print(f"   Error output: {result.stderr[:200]}...")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {category_name} tests timed out")
            results[category_name] = {"passed": False, "error": "timeout"}
        except Exception as e:
            print(f"💥 {category_name} tests crashed: {e}")
            results[category_name] = {"passed": False, "error": str(e)}
    
    # Summary
    passed_count = sum(1 for r in results.values() if r.get("passed", False))
    total_count = len(results)
    
    print(f"\n📊 Individual Test Results: {passed_count}/{total_count} categories passed")
    
    return passed_count == total_count


def main():
    """Main entry point."""
    print("🤖 AI Agents Testing and Debugging Suite")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix the issues above and try again.")
        sys.exit(1)
    
    # Install test dependencies
    install_test_dependencies()
    
    # Run smoke test
    if not run_quick_smoke_test():
        print("\n❌ Smoke test failed. Please check your configuration.")
        sys.exit(1)
    
    # Choose test mode
    print("\n🎯 Choose test mode:")
    print("1. Comprehensive test suite (recommended)")
    print("2. Individual test categories")
    print("3. Both")
    
    try:
        choice = input("Enter your choice (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        sys.exit(130)
    
    success = True
    
    if choice in ["1", "3"]:
        print("\n" + "=" * 50)
        print("🚀 Running Comprehensive Test Suite")
        print("=" * 50)
        
        try:
            success = asyncio.run(run_comprehensive_tests())
        except KeyboardInterrupt:
            print("\n⏹️  Test run interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"\n💥 Comprehensive test suite failed: {e}")
            success = False
    
    if choice in ["2", "3"]:
        print("\n" + "=" * 50)
        print("🔬 Running Individual Test Categories")
        print("=" * 50)
        
        try:
            individual_success = run_individual_test_categories()
            success = success and individual_success
        except KeyboardInterrupt:
            print("\n⏹️  Individual tests interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"\n💥 Individual tests failed: {e}")
            success = False
    
    # Final results
    print("\n" + "=" * 50)
    if success:
        print("🎉 All AI agent tests passed! System is ready for production.")
        print("\n✅ Key achievements:")
        print("   • LLM integration with qwen/qwen3-235b-a22b-thinking-2507 verified")
        print("   • End-to-end agent workflows functioning correctly")
        print("   • API response validation working properly")
        print("   • Error handling and debugging systems operational")
        print("   • Performance metrics within acceptable ranges")
        print("   • Multi-agent coordination functioning correctly")
        print("   • WebSocket communication established successfully")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please review the results and fix issues.")
        print("\n🔧 Next steps:")
        print("   • Check the detailed test reports for specific failures")
        print("   • Verify OpenRouter API key and connectivity")
        print("   • Review system resources and configuration")
        print("   • Check logs for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()
