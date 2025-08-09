#!/usr/bin/env python3
"""
Script to run database seeding for Phase 15B integration testing.

This script sets up the Python path and runs the seeding script with proper
environment configuration.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set environment variables for testing
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_integration.db")

# Import and run the seeding script
from scripts.seed_integration_data import main

if __name__ == "__main__":
    print("Starting Phase 15B database seeding...")
    main()
    print("Seeding completed!")
