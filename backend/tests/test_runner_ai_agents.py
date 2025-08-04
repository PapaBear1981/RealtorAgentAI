"""
Comprehensive Test Runner for AI Agents Testing and Debugging.

This module provides a comprehensive test runner that executes all AI agent tests
and provides detailed reporting on LLM integration, performance, and functionality.
"""

import asyncio
import pytest
import sys
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

import structlog
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text

from app.core.config import get_settings
from app.services.model_router import ModelRouter
from app.services.agent_orchestrator import AgentOrchestrator

logger = structlog.get_logger(__name__)
console = Console()


class AIAgentTestRunner:
    """Comprehensive test runner for AI agent testing and debugging."""

    def __init__(self):
        self.settings = get_settings()
        self.test_results = {}
        self.performance_metrics = {}
        self.error_log = []

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all AI agent tests and return comprehensive results."""
        console.print(Panel.fit("🤖 AI Agents Testing and Debugging Suite", style="bold blue"))
        
        # Pre-flight checks
        await self._run_preflight_checks()
        
        # Test categories
        test_categories = [
            ("LLM Integration", self._run_llm_integration_tests),
            ("End-to-End Workflows", self._run_e2e_workflow_tests),
            ("API Response Validation", self._run_api_validation_tests),
            ("Error Handling", self._run_error_handling_tests),
            ("Performance", self._run_performance_tests),
            ("Integration Coordination", self._run_integration_tests),
            ("WebSocket Communication", self._run_websocket_tests)
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            for category_name, test_func in test_categories:
                task = progress.add_task(f"Running {category_name} tests...", total=1)
                
                try:
                    results = await test_func()
                    self.test_results[category_name] = results
                    progress.update(task, completed=1)
                    
                except Exception as e:
                    self.error_log.append(f"{category_name}: {str(e)}")
                    self.test_results[category_name] = {"status": "failed", "error": str(e)}
                    progress.update(task, completed=1)

        # Generate comprehensive report
        return await self._generate_comprehensive_report()

    async def _run_preflight_checks(self) -> Dict[str, Any]:
        """Run pre-flight checks to ensure system is ready for testing."""
        console.print("🔍 Running pre-flight checks...")
        
        checks = {
            "openrouter_api_key": bool(self.settings.OPENROUTER_API_KEY),
            "model_router_initialization": False,
            "agent_orchestrator_initialization": False,
            "qwen_model_availability": False
        }

        try:
            # Test model router initialization
            router = ModelRouter()
            await router.initialize()
            checks["model_router_initialization"] = True

            # Test agent orchestrator initialization
            orchestrator = AgentOrchestrator()
            await orchestrator.initialize()
            checks["agent_orchestrator_initialization"] = True

            # Test Qwen model availability
            from app.services.model_router import ModelRequest
            test_request = ModelRequest(
                messages=[{"role": "user", "content": "Test"}],
                model_preference="qwen/qwen3-235b-a22b-thinking-2507",
                max_tokens=10
            )
            
            response = await router.generate_response(test_request)
            if response and response.model_used == "qwen/qwen3-235b-a22b-thinking-2507":
                checks["qwen_model_availability"] = True

        except Exception as e:
            self.error_log.append(f"Pre-flight check failed: {str(e)}")

        # Display results
        table = Table(title="Pre-flight Check Results")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")

        for check, status in checks.items():
            status_text = "✅ PASS" if status else "❌ FAIL"
            table.add_row(check.replace("_", " ").title(), status_text)

        console.print(table)
        return checks

    async def _run_llm_integration_tests(self) -> Dict[str, Any]:
        """Run LLM integration tests."""
        console.print("🧠 Testing LLM Integration...")
        
        # Run pytest for LLM integration tests
        exit_code = pytest.main([
            "tests/test_llm_integration.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results_llm.json"
        ])

        results = {
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Load detailed results if available
        try:
            with open("test_results_llm.json", "r") as f:
                detailed_results = json.load(f)
                results["detailed"] = detailed_results
        except:
            pass

        return results

    async def _run_e2e_workflow_tests(self) -> Dict[str, Any]:
        """Run end-to-end workflow tests."""
        console.print("🔄 Testing End-to-End Workflows...")
        
        exit_code = pytest.main([
            "tests/test_end_to_end_workflows.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results_e2e.json"
        ])

        return {
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _run_api_validation_tests(self) -> Dict[str, Any]:
        """Run API response validation tests."""
        console.print("✅ Testing API Response Validation...")
        
        exit_code = pytest.main([
            "tests/test_api_response_validation.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results_api.json"
        ])

        return {
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _run_error_handling_tests(self) -> Dict[str, Any]:
        """Run error handling and debugging tests."""
        console.print("🚨 Testing Error Handling...")
        
        exit_code = pytest.main([
            "tests/test_error_handling_debugging.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results_error.json"
        ])

        return {
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        console.print("⚡ Testing Performance...")
        
        exit_code = pytest.main([
            "tests/test_performance.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results_performance.json"
        ])

        # Collect performance metrics
        try:
            with open("test_results_performance.json", "r") as f:
                perf_data = json.load(f)
                self.performance_metrics = perf_data
        except:
            pass

        return {
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration coordination tests."""
        console.print("🤝 Testing Integration Coordination...")
        
        exit_code = pytest.main([
            "tests/test_integration_coordination.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results_integration.json"
        ])

        return {
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _run_websocket_tests(self) -> Dict[str, Any]:
        """Run WebSocket communication tests."""
        console.print("🌐 Testing WebSocket Communication...")
        
        exit_code = pytest.main([
            "tests/test_websocket_communication.py",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=test_results_websocket.json"
        ])

        return {
            "exit_code": exit_code,
            "status": "passed" if exit_code == 0 else "failed",
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        console.print("\n📊 Generating Comprehensive Report...")
        
        # Summary statistics
        total_categories = len(self.test_results)
        passed_categories = sum(1 for r in self.test_results.values() if r.get("status") == "passed")
        failed_categories = total_categories - passed_categories

        # Create summary table
        summary_table = Table(title="🤖 AI Agents Testing Summary")
        summary_table.add_column("Category", style="cyan")
        summary_table.add_column("Status", style="green")
        summary_table.add_column("Details")

        for category, results in self.test_results.items():
            status = results.get("status", "unknown")
            status_emoji = "✅" if status == "passed" else "❌"
            status_text = f"{status_emoji} {status.upper()}"
            
            details = ""
            if "error" in results:
                details = results["error"][:50] + "..." if len(results["error"]) > 50 else results["error"]
            
            summary_table.add_row(category, status_text, details)

        console.print(summary_table)

        # Overall status
        overall_status = "PASSED" if failed_categories == 0 else "FAILED"
        status_color = "green" if overall_status == "PASSED" else "red"
        
        console.print(f"\n🎯 Overall Status: [{status_color}]{overall_status}[/{status_color}]")
        console.print(f"📈 Categories Passed: {passed_categories}/{total_categories}")
        
        if self.error_log:
            console.print("\n🚨 Errors Encountered:")
            for error in self.error_log:
                console.print(f"  • {error}", style="red")

        # Performance summary
        if self.performance_metrics:
            console.print("\n⚡ Performance Highlights:")
            # Add performance metrics display here

        # Generate report data
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "summary": {
                "total_categories": total_categories,
                "passed_categories": passed_categories,
                "failed_categories": failed_categories,
                "success_rate": passed_categories / total_categories if total_categories > 0 else 0
            },
            "category_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "errors": self.error_log,
            "recommendations": self._generate_recommendations()
        }

        # Save report to file
        report_file = f"ai_agents_test_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        console.print(f"\n📄 Detailed report saved to: {report_file}")
        
        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Check for common issues
        if not self.settings.OPENROUTER_API_KEY:
            recommendations.append("Configure OPENROUTER_API_KEY environment variable")

        failed_categories = [cat for cat, result in self.test_results.items() 
                           if result.get("status") == "failed"]

        if "LLM Integration" in failed_categories:
            recommendations.append("Check OpenRouter API connectivity and model availability")

        if "Performance" in failed_categories:
            recommendations.append("Review system resources and optimize agent configurations")

        if "WebSocket Communication" in failed_categories:
            recommendations.append("Verify WebSocket server configuration and network connectivity")

        if len(failed_categories) > len(self.test_results) / 2:
            recommendations.append("Consider reviewing overall system configuration")

        return recommendations


async def main():
    """Main entry point for the test runner."""
    runner = AIAgentTestRunner()
    
    try:
        results = await runner.run_comprehensive_tests()
        
        # Exit with appropriate code
        if results["overall_status"] == "PASSED":
            console.print("\n🎉 All tests passed! AI Agents are ready for production.", style="bold green")
            sys.exit(0)
        else:
            console.print("\n⚠️  Some tests failed. Please review the results and fix issues.", style="bold red")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n⏹️  Test run interrupted by user.", style="yellow")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n💥 Test runner failed: {str(e)}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
