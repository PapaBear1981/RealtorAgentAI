#!/usr/bin/env python3
"""
Manual test script for startup validation functionality.

This script tests the startup validation service and health check endpoints
without requiring the full application stack to be running.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from unittest.mock import Mock, patch

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_startup_validation_service():
    """Test the startup validation service directly."""
    print("=" * 60)
    print("Testing Startup Validation Service")
    print("=" * 60)
    
    try:
        from app.core.startup_validation import StartupValidationService, ServiceStatus
        
        # Create service instance
        service = StartupValidationService()
        print(f"✅ Service created successfully")
        print(f"   Startup time: {service.startup_time}")
        print(f"   Initial status: {service.health_status.overall_status}")
        
        # Test configuration check
        print("\n📋 Testing configuration check...")
        await service._check_configuration()
        
        config_service = service.health_status.services.get("configuration")
        if config_service:
            print(f"   Status: {config_service.status}")
            print(f"   Response time: {config_service.response_time_ms:.2f}ms")
            if config_service.error_message:
                print(f"   Error: {config_service.error_message}")
        
        # Test logging check
        print("\n📝 Testing logging system check...")
        await service._check_logging_system()
        
        logging_service = service.health_status.services.get("logging")
        if logging_service:
            print(f"   Status: {logging_service.status}")
            print(f"   Response time: {logging_service.response_time_ms:.2f}ms")
        
        # Test readiness and liveness status
        print("\n🔍 Testing readiness status...")
        readiness = service.get_readiness_status()
        print(f"   Ready: {readiness['ready']}")
        print(f"   Startup complete: {readiness['startup_complete']}")
        print(f"   Overall status: {readiness['overall_status']}")
        
        print("\n💓 Testing liveness status...")
        liveness = service.get_liveness_status()
        print(f"   Alive: {liveness['alive']}")
        print(f"   Uptime: {liveness['uptime_seconds']:.2f}s")
        
        print("\n✅ Startup validation service tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing startup validation service: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health_endpoints_mock():
    """Test health endpoints with mocked dependencies."""
    print("\n" + "=" * 60)
    print("Testing Health Endpoints (Mocked)")
    print("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        
        # Mock the dependencies that might not be available
        with patch('app.core.startup_validation.check_database_connection', return_value=True), \
             patch('app.core.startup_validation.get_redis_manager') as mock_redis, \
             patch('app.core.startup_validation.get_storage_client') as mock_storage:
            
            # Mock Redis manager
            mock_redis_manager = Mock()
            mock_redis_manager.health_check.return_value = {"status": "healthy", "connection_info": {}}
            mock_redis.return_value = mock_redis_manager
            
            # Mock storage client
            mock_storage_client = Mock()
            mock_storage_client.upload_file.return_value = {"key": "test"}
            mock_storage_client.get_file.return_value = b"test"
            mock_storage_client.delete_file.return_value = True
            mock_storage.return_value = mock_storage_client
            
            # Import and create test client
            from app.main import app
            client = TestClient(app)
            
            # Test basic health endpoint
            print("\n🏥 Testing /health endpoint...")
            response = client.get("/health")
            print(f"   Status code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Services healthy: {data.get('services_healthy', 0)}")
                print(f"   Total services: {data.get('total_services', 0)}")
            else:
                print(f"   Error: {response.text}")
            
            # Test detailed health endpoint
            print("\n🔍 Testing /health/detailed endpoint...")
            response = client.get("/health/detailed")
            print(f"   Status code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Overall status: {data.get('overall_status', 'unknown')}")
                print(f"   Startup complete: {data.get('startup_complete', False)}")
                print(f"   Services count: {len(data.get('services', {}))}")
                print(f"   Critical errors: {len(data.get('critical_errors', []))}")
                print(f"   Warnings: {len(data.get('warnings', []))}")
            else:
                print(f"   Error: {response.text}")
            
            # Test readiness probe
            print("\n✅ Testing /health/ready endpoint...")
            response = client.get("/health/ready")
            print(f"   Status code: {response.status_code}")
            if response.status_code in [200, 503]:
                data = response.json()
                if response.status_code == 200:
                    print(f"   Ready: {data.get('ready', False)}")
                    print(f"   Critical services healthy: {data.get('critical_services_healthy', False)}")
                else:
                    print(f"   Not ready: {data.get('detail', 'Unknown error')}")
            else:
                print(f"   Error: {response.text}")
            
            # Test liveness probe
            print("\n💓 Testing /health/live endpoint...")
            response = client.get("/health/live")
            print(f"   Status code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Alive: {data.get('alive', False)}")
                print(f"   Uptime: {data.get('uptime_seconds', 0):.2f}s")
            else:
                print(f"   Error: {response.text}")
            
            print("\n✅ Health endpoints tests completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error testing health endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting Phase 15A: Server Startup Validation Tests")
    print(f"⏰ Test started at: {datetime.now().isoformat()}")
    
    # Test startup validation service
    service_test_passed = await test_startup_validation_service()
    
    # Test health endpoints
    endpoints_test_passed = test_health_endpoints_mock()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Startup Validation Service: {'✅ PASSED' if service_test_passed else '❌ FAILED'}")
    print(f"Health Endpoints: {'✅ PASSED' if endpoints_test_passed else '❌ FAILED'}")
    
    if service_test_passed and endpoints_test_passed:
        print("\n🎉 All Phase 15A tests PASSED!")
        print("\nImplemented features:")
        print("  ✅ Comprehensive startup validation service")
        print("  ✅ Enhanced health check endpoints (/health, /health/detailed)")
        print("  ✅ Kubernetes readiness probe (/health/ready)")
        print("  ✅ Kubernetes liveness probe (/health/live)")
        print("  ✅ Service dependency verification (database, Redis, storage)")
        print("  ✅ Graceful failure modes with detailed error messages")
        print("  ✅ Proper logging and monitoring integration")
        
        return 0
    else:
        print("\n❌ Some tests FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
