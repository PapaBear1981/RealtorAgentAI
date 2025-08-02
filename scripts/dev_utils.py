#!/usr/bin/env python3
"""
Development Utilities
Multi-Agent Real-Estate Contract Platform

Collection of utility functions for development tasks including:
- Environment validation
- Database management
- Service health checks
- Development data generation

Usage:
    python scripts/dev_utils.py <command> [options]
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

def find_repo_root():
    """Find the repository root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Not in a git repository")

def run_command(command: str, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def validate_environment():
    """Validate development environment setup."""
    print("🔍 Validating development environment...")
    
    repo_root = find_repo_root()
    issues = []
    
    # Check required files
    required_files = [
        ".env.example",
        "docker-compose.yml",
        ".pre-commit-config.yaml",
        ".editorconfig",
        "requirements-dev.txt"
    ]
    
    for file_path in required_files:
        if not (repo_root / file_path).exists():
            issues.append(f"Missing required file: {file_path}")
    
    # Check virtual environment
    venv_path = repo_root / ".venv"
    if not venv_path.exists():
        issues.append("Virtual environment not found (.venv)")
    
    # Check .env file
    env_file = repo_root / ".env"
    if not env_file.exists():
        issues.append(".env file not found (copy from .env.example)")
    
    # Check Docker
    try:
        result = run_command("docker --version", check=False)
        if result.returncode != 0:
            issues.append("Docker not installed or not accessible")
    except Exception:
        issues.append("Docker not installed or not accessible")
    
    # Check Docker Compose
    try:
        result = run_command("docker-compose --version", check=False)
        if result.returncode != 0:
            issues.append("Docker Compose not installed or not accessible")
    except Exception:
        issues.append("Docker Compose not installed or not accessible")
    
    if issues:
        print("❌ Environment validation failed:")
        for issue in issues:
            print(f"  • {issue}")
        return False
    else:
        print("✅ Environment validation passed!")
        return True

def check_services_health():
    """Check health of development services."""
    print("🏥 Checking service health...")
    
    services = {
        "Backend API": "http://localhost:8000/health",
        "Frontend": "http://localhost:3000",
        "Redis": "redis://localhost:6379",
        "MinIO": "http://localhost:9000/minio/health/live",
        "Celery Flower": "http://localhost:5555"
    }
    
    healthy_services = []
    unhealthy_services = []
    
    for service_name, endpoint in services.items():
        try:
            if endpoint.startswith("redis://"):
                # Special handling for Redis
                result = run_command("redis-cli ping", check=False)
                if result.returncode == 0 and "PONG" in result.stdout:
                    healthy_services.append(service_name)
                else:
                    unhealthy_services.append(service_name)
            else:
                # HTTP health check
                result = run_command(f"curl -f {endpoint}", check=False)
                if result.returncode == 0:
                    healthy_services.append(service_name)
                else:
                    unhealthy_services.append(service_name)
        except Exception:
            unhealthy_services.append(service_name)
    
    print(f"✅ Healthy services ({len(healthy_services)}):")
    for service in healthy_services:
        print(f"  • {service}")
    
    if unhealthy_services:
        print(f"❌ Unhealthy services ({len(unhealthy_services)}):")
        for service in unhealthy_services:
            print(f"  • {service}")
        print("\n💡 Try running: docker-compose up -d")
    
    return len(unhealthy_services) == 0

def start_services():
    """Start development services."""
    print("🚀 Starting development services...")
    
    repo_root = find_repo_root()
    
    # Start Docker services
    result = run_command("docker-compose up -d", cwd=repo_root)
    if result.returncode == 0:
        print("✅ Docker services started")
        
        # Wait a moment for services to initialize
        print("⏳ Waiting for services to initialize...")
        time.sleep(10)
        
        # Check health
        check_services_health()
    else:
        print("❌ Failed to start Docker services")
        return False
    
    return True

def stop_services():
    """Stop development services."""
    print("🛑 Stopping development services...")
    
    repo_root = find_repo_root()
    result = run_command("docker-compose down", cwd=repo_root)
    
    if result.returncode == 0:
        print("✅ Services stopped")
        return True
    else:
        print("❌ Failed to stop services")
        return False

def reset_database():
    """Reset development database."""
    print("🗄️ Resetting development database...")
    
    repo_root = find_repo_root()
    db_path = repo_root / "database" / "database.db"
    
    if db_path.exists():
        db_path.unlink()
        print("✅ Database file removed")
    
    # TODO: Run database migrations when they're implemented
    print("💡 Remember to run database migrations after implementing them")
    
    return True

def generate_test_data():
    """Generate test data for development."""
    print("📊 Generating test data...")
    
    # TODO: Implement test data generation
    print("💡 Test data generation not yet implemented")
    print("   This will be added when the database models are ready")
    
    return True

def run_code_quality_checks():
    """Run code quality checks."""
    print("🔍 Running code quality checks...")
    
    repo_root = find_repo_root()
    venv_path = repo_root / ".venv"
    
    if not venv_path.exists():
        print("❌ Virtual environment not found")
        return False
    
    # Determine the correct pre-commit path
    if os.name == 'nt':  # Windows
        pre_commit_cmd = str(venv_path / "Scripts" / "pre-commit")
    else:  # Unix-like
        pre_commit_cmd = str(venv_path / "bin" / "pre-commit")
    
    # Run pre-commit on all files
    result = run_command(f"{pre_commit_cmd} run --all-files", cwd=repo_root, check=False)
    
    if result.returncode == 0:
        print("✅ All code quality checks passed")
        return True
    else:
        print("❌ Code quality checks failed")
        print("💡 Fix the issues and run again")
        return False

def show_development_status():
    """Show comprehensive development environment status."""
    print("📊 Development Environment Status")
    print("=" * 50)
    
    # Environment validation
    env_valid = validate_environment()
    print()
    
    # Service health
    services_healthy = check_services_health()
    print()
    
    # Overall status
    if env_valid and services_healthy:
        print("🎉 Development environment is ready!")
        print("\n📋 Quick commands:")
        print("  • Start coding: Open your IDE and start developing")
        print("  • Run tests: pytest (backend) or npm test (frontend)")
        print("  • Check code quality: python scripts/dev_utils.py quality")
        print("  • View services: docker-compose ps")
    else:
        print("⚠️  Development environment needs attention")
        print("\n🔧 Suggested fixes:")
        if not env_valid:
            print("  • Run: python scripts/setup_dev_env.py")
        if not services_healthy:
            print("  • Run: python scripts/dev_utils.py start")

def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Development utilities for Real Estate Contract Platform")
    parser.add_argument("command", choices=[
        "validate", "health", "start", "stop", "reset-db", 
        "test-data", "quality", "status"
    ], help="Command to run")
    
    args = parser.parse_args()
    
    try:
        if args.command == "validate":
            success = validate_environment()
        elif args.command == "health":
            success = check_services_health()
        elif args.command == "start":
            success = start_services()
        elif args.command == "stop":
            success = stop_services()
        elif args.command == "reset-db":
            success = reset_database()
        elif args.command == "test-data":
            success = generate_test_data()
        elif args.command == "quality":
            success = run_code_quality_checks()
        elif args.command == "status":
            show_development_status()
            success = True
        else:
            print(f"Unknown command: {args.command}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
