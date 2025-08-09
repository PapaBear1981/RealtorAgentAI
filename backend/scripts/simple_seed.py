#!/usr/bin/env python3
"""
Simple database seeding script for testing.
Creates basic users for authentication testing.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import create_engine, Session
from app.core.config import get_settings
from app.core.auth import hash_password
from app.models.user import User
from app.core.database import create_db_and_tables

def create_test_users():
    """Create basic test users for authentication testing."""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)

    # Create tables
    create_db_and_tables()

    # Test users data
    users_data = [
        {
            "email": "admin@example.com",
            "name": "Admin User",
            "role": "admin",
            "password": "password123"
        },
        {
            "email": "agent@example.com",
            "name": "Real Estate Agent",
            "role": "agent",
            "password": "password123"
        },
        {
            "email": "tc@example.com",
            "name": "Transaction Coordinator",
            "role": "tc",
            "password": "password123"
        },
        {
            "email": "signer@example.com",
            "name": "Document Signer",
            "role": "signer",
            "password": "password123"
        }
    ]

    with Session(engine) as session:
        # Clear existing users
        session.query(User).delete()
        session.commit()

        # Create new users
        for user_data in users_data:
            user = User(
                email=user_data["email"],
                name=user_data["name"],
                role=user_data["role"],
                password_hash=hash_password(user_data["password"]),
                disabled=False
            )
            session.add(user)
            print(f"Created user: {user.email} ({user.role})")

        session.commit()
        print(f"Successfully created {len(users_data)} test users")

if __name__ == "__main__":
    try:
        create_test_users()
        print("✅ Simple seeding completed successfully!")
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        sys.exit(1)
