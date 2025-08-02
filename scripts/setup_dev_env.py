#!/usr/bin/env python3
"""
Development Environment Setup Script
Multi-Agent Real-Estate Contract Platform

This script sets up the complete development environment including:
- Python virtual environment
- Development dependencies
- Pre-commit hooks
- Environment validation

Usage:
    python scripts/setup_dev_env.py
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, cwd=None, check=True):
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
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def find_repo_root():
    """Find the repository root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Not in a git repository")

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major != 3 or version.minor < 11:
        print(f"Error: Python 3.11+ required, found {version.major}.{version.minor}")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")

def setup_virtual_environment(repo_root):
    """Set up Python virtual environment."""
    venv_path = repo_root / ".venv"
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return venv_path
    
    print("📦 Creating virtual environment...")
    run_command(f"python -m venv {venv_path}", cwd=repo_root)
    print("✅ Virtual environment created")
    return venv_path

def get_activation_command(venv_path):
    """Get the appropriate activation command for the platform."""
    if platform.system() == "Windows":
        return f"{venv_path}\\Scripts\\activate"
    else:
        return f"source {venv_path}/bin/activate"

def install_dependencies(repo_root, venv_path):
    """Install development dependencies."""
    print("📦 Installing development dependencies...")
    
    # Get activation command
    if platform.system() == "Windows":
        pip_cmd = f"{venv_path}\\Scripts\\pip"
    else:
        pip_cmd = f"{venv_path}/bin/pip"
    
    # Upgrade pip
    run_command(f"{pip_cmd} install --upgrade pip", cwd=repo_root)
    
    # Install development dependencies
    run_command(f"{pip_cmd} install -r requirements-dev.txt", cwd=repo_root)
    
    print("✅ Development dependencies installed")

def setup_pre_commit(repo_root, venv_path):
    """Set up pre-commit hooks."""
    print("🔧 Setting up pre-commit hooks...")
    
    if platform.system() == "Windows":
        pre_commit_cmd = f"{venv_path}\\Scripts\\pre-commit"
    else:
        pre_commit_cmd = f"{venv_path}/bin/pre-commit"
    
    # Install pre-commit hooks
    run_command(f"{pre_commit_cmd} install", cwd=repo_root)
    
    # Create secrets baseline if it doesn't exist
    secrets_baseline = repo_root / ".secrets.baseline"
    if not secrets_baseline.exists():
        print("🔐 Creating secrets baseline...")
        if platform.system() == "Windows":
            detect_secrets_cmd = f"{venv_path}\\Scripts\\detect-secrets"
        else:
            detect_secrets_cmd = f"{venv_path}/bin/detect-secrets"
        
        run_command(f"{detect_secrets_cmd} scan . > .secrets.baseline", cwd=repo_root)
    
    print("✅ Pre-commit hooks configured")

def validate_environment(repo_root):
    """Validate the development environment setup."""
    print("🔍 Validating environment setup...")
    
    # Check required files
    required_files = [
        ".venv",
        ".pre-commit-config.yaml",
        ".editorconfig",
        ".secrets.baseline",
        "requirements-dev.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (repo_root / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files present")
    return True

def create_env_example_if_missing(repo_root):
    """Create .env.example if it doesn't exist."""
    env_example = repo_root / ".env.example"
    if env_example.exists():
        print("✅ .env.example already exists")
        return
    
    print("📝 .env.example not found - it should have been created earlier")
    print("   Please ensure .env.example exists with proper environment variables")

def print_next_steps(repo_root, venv_path):
    """Print next steps for the developer."""
    activation_cmd = get_activation_command(venv_path)
    
    print("\n🎉 Development environment setup complete!")
    print("\n📋 Next steps:")
    print(f"1. Activate the virtual environment:")
    if platform.system() == "Windows":
        print(f"   .venv\\Scripts\\activate")
    else:
        print(f"   source .venv/bin/activate")
    
    print("\n2. Copy and configure environment variables:")
    print("   cp .env.example .env")
    print("   # Edit .env with your actual values")
    
    print("\n3. Start development services:")
    print("   docker-compose up -d")
    
    print("\n4. Run pre-commit on all files (optional):")
    if platform.system() == "Windows":
        print("   .venv\\Scripts\\pre-commit run --all-files")
    else:
        print("   .venv/bin/pre-commit run --all-files")
    
    print("\n5. Start coding! The pre-commit hooks will ensure code quality.")
    
    print(f"\n📚 Documentation:")
    print(f"   - Development rules: development-rules/")
    print(f"   - Task verification: TASK_VERIFICATION_GUIDE.md")
    print(f"   - Project structure: PROJECT_STRUCTURE.md")

def main():
    """Main setup function."""
    print("🚀 Setting up development environment...")
    print("=" * 50)
    
    try:
        # Find repository root
        repo_root = find_repo_root()
        print(f"📁 Repository root: {repo_root}")
        
        # Check Python version
        check_python_version()
        
        # Set up virtual environment
        venv_path = setup_virtual_environment(repo_root)
        
        # Install dependencies
        install_dependencies(repo_root, venv_path)
        
        # Set up pre-commit
        setup_pre_commit(repo_root, venv_path)
        
        # Validate environment
        if not validate_environment(repo_root):
            print("❌ Environment validation failed")
            sys.exit(1)
        
        # Check .env.example
        create_env_example_if_missing(repo_root)
        
        # Print next steps
        print_next_steps(repo_root, venv_path)
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
