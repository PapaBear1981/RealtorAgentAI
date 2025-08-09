#!/usr/bin/env python3
"""
Comprehensive database seeding script for Phase 15B integration testing.

This script creates realistic test data for the Multi-Agent Real-Estate Contract Platform,
including users, deals, contracts, templates, files, and AI agent interactions.

Usage:
    python backend/scripts/seed_integration_data.py [--reset] [--scenario=<scenario>]

Scenarios:
    - basic: Basic test data for development
    - comprehensive: Full test data for integration testing
    - performance: Large dataset for performance testing
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import random
from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.exc import IntegrityError

# Import all models
from app.models import (
    User, Deal, Upload, Contract, Template, Version, Signer, SignEvent,
    Validation, AuditLog, File, SignatureRequest, AgentExecution,
    AgentPerformanceMetric, ContractProcessingMetric, CostTracking,
    UserBehaviorEvent, WorkflowPattern, PredictiveModel, AnalyticsReport
)
from app.core.config import get_settings
from app.core.auth import hash_password

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class DatabaseSeeder:
    """Database seeding service for integration testing."""

    def __init__(self, engine):
        self.engine = engine
        self.session = Session(engine)

    def reset_database(self):
        """Reset database by dropping and recreating all tables."""
        logger.info("Resetting database...")
        SQLModel.metadata.drop_all(self.engine)
        SQLModel.metadata.create_all(self.engine)
        logger.info("Database reset complete")

    def seed_users(self) -> List[User]:
        """Seed user accounts with different roles."""
        logger.info("Seeding users...")

        users_data = [
            {
                "email": "admin@realestate.com",
                "name": "System Administrator",
                "role": "admin",
                "password": "admin123"
            },
            {
                "email": "john.agent@realestate.com",
                "name": "John Smith",
                "role": "agent",
                "password": "agent123"
            },
            {
                "email": "sarah.agent@realestate.com",
                "name": "Sarah Johnson",
                "role": "agent",
                "password": "agent123"
            },
            {
                "email": "mike.tc@realestate.com",
                "name": "Mike Wilson",
                "role": "tc",
                "password": "tc123"
            },
            {
                "email": "buyer1@email.com",
                "name": "Robert Davis",
                "role": "signer",
                "password": "signer123"
            },
            {
                "email": "seller1@email.com",
                "name": "Lisa Brown",
                "role": "signer",
                "password": "signer123"
            },
            {
                "email": "buyer2@email.com",
                "name": "David Miller",
                "role": "signer",
                "password": "signer123"
            },
            {
                "email": "seller2@email.com",
                "name": "Jennifer Garcia",
                "role": "signer",
                "password": "signer123"
            }
        ]

        users = []
        for user_data in users_data:
            try:
                user = User(
                    email=user_data["email"],
                    name=user_data["name"],
                    role=user_data["role"],
                    password_hash=hash_password(user_data["password"]),
                    disabled=False
                )
                self.session.add(user)
                self.session.commit()
                self.session.refresh(user)
                users.append(user)
                logger.info(f"Created user: {user.email} ({user.role})")
            except IntegrityError:
                self.session.rollback()
                # User already exists, fetch it
                existing_user = self.session.exec(
                    select(User).where(User.email == user_data["email"])
                ).first()
                if existing_user:
                    users.append(existing_user)
                    logger.info(f"User already exists: {user_data['email']}")

        return users

    def seed_templates(self) -> List[Template]:
        """Seed contract templates."""
        logger.info("Seeding templates...")

        templates_data = [
            {
                "name": "California Residential Purchase Agreement",
                "version": "2024.1",
                "docx_key": "templates/ca_residential_purchase.docx",
                "schema": {
                    "buyer_name": {"type": "string", "required": True},
                    "seller_name": {"type": "string", "required": True},
                    "property_address": {"type": "string", "required": True},
                    "purchase_price": {"type": "number", "required": True},
                    "earnest_money": {"type": "number", "required": True},
                    "closing_date": {"type": "date", "required": True},
                    "financing_type": {"type": "string", "required": False}
                },
                "ruleset": {
                    "required_fields": ["buyer_name", "seller_name", "property_address", "purchase_price"],
                    "validation_rules": {
                        "purchase_price": {"min": 1000, "max": 50000000},
                        "earnest_money": {"min": 100, "max": 1000000}
                    }
                },
                "description": "Standard residential purchase agreement for California properties"
            },
            {
                "name": "Exclusive Right to Sell Listing Agreement",
                "version": "2024.1",
                "docx_key": "templates/listing_agreement.docx",
                "schema": {
                    "seller_name": {"type": "string", "required": True},
                    "agent_name": {"type": "string", "required": True},
                    "property_address": {"type": "string", "required": True},
                    "listing_price": {"type": "number", "required": True},
                    "commission_rate": {"type": "number", "required": True},
                    "listing_period": {"type": "number", "required": True}
                },
                "ruleset": {
                    "required_fields": ["seller_name", "agent_name", "property_address", "listing_price"],
                    "validation_rules": {
                        "commission_rate": {"min": 0.01, "max": 0.10},
                        "listing_period": {"min": 30, "max": 365}
                    }
                },
                "description": "Exclusive listing agreement for residential properties"
            },
            {
                "name": "Residential Lease Agreement",
                "version": "2024.1",
                "docx_key": "templates/lease_agreement.docx",
                "schema": {
                    "landlord_name": {"type": "string", "required": True},
                    "tenant_name": {"type": "string", "required": True},
                    "property_address": {"type": "string", "required": True},
                    "monthly_rent": {"type": "number", "required": True},
                    "security_deposit": {"type": "number", "required": True},
                    "lease_term": {"type": "number", "required": True},
                    "start_date": {"type": "date", "required": True}
                },
                "ruleset": {
                    "required_fields": ["landlord_name", "tenant_name", "property_address", "monthly_rent"],
                    "validation_rules": {
                        "monthly_rent": {"min": 500, "max": 50000},
                        "lease_term": {"min": 1, "max": 60}
                    }
                },
                "description": "Standard residential lease agreement"
            }
        ]

        templates = []
        for template_data in templates_data:
            try:
                template = Template(
                    name=template_data["name"],
                    version=template_data["version"],
                    docx_key=template_data["docx_key"],
                    schema=template_data["schema"],
                    ruleset=template_data["ruleset"],
                    description=template_data.get("description", ""),
                    is_active=True,
                    usage_count=0
                )
                self.session.add(template)
                self.session.commit()
                self.session.refresh(template)
                templates.append(template)
                logger.info(f"Created template: {template.name}")
            except IntegrityError:
                self.session.rollback()
                logger.warning(f"Template already exists: {template_data['name']}")

        return templates

    def seed_deals(self, users: List[User]) -> List[Deal]:
        """Seed real estate deals."""
        logger.info("Seeding deals...")

        # Get agents for deal ownership
        agents = [u for u in users if u.role == "agent"]

        deals_data = [
            {
                "title": "Davis Family Home Purchase - 123 Oak Street",
                "status": "active",
                "property_address": "123 Oak Street, San Francisco, CA 94102"
            },
            {
                "title": "Miller Condo Sale - 456 Pine Avenue",
                "status": "pending",
                "property_address": "456 Pine Avenue, Los Angeles, CA 90210"
            },
            {
                "title": "Garcia Investment Property - 789 Elm Drive",
                "status": "active",
                "property_address": "789 Elm Drive, San Diego, CA 92101"
            },
            {
                "title": "Johnson Townhouse Listing - 321 Maple Lane",
                "status": "active",
                "property_address": "321 Maple Lane, Sacramento, CA 95814"
            },
            {
                "title": "Brown Estate Sale - 654 Cedar Court",
                "status": "closed",
                "property_address": "654 Cedar Court, Fresno, CA 93701"
            }
        ]

        deals = []
        for i, deal_data in enumerate(deals_data):
            try:
                deal = Deal(
                    title=deal_data["title"],
                    status=deal_data["status"],
                    owner_id=agents[i % len(agents)].id,
                    property_address=deal_data.get("property_address", "")
                )
                self.session.add(deal)
                self.session.commit()
                self.session.refresh(deal)
                deals.append(deal)
                logger.info(f"Created deal: {deal.title}")
            except IntegrityError:
                self.session.rollback()
                logger.warning(f"Deal already exists: {deal_data['title']}")

        return deals

    def seed_contracts(self, deals: List[Deal], templates: List[Template], users: List[User]) -> List[Contract]:
        """Seed contracts for deals."""
        logger.info("Seeding contracts...")

        contracts = []
        for i, deal in enumerate(deals[:3]):  # Create contracts for first 3 deals
            template = templates[i % len(templates)]

            # Sample contract variables based on template type
            if "Purchase" in template.name:
                variables = {
                    "buyer_name": "Robert Davis",
                    "seller_name": "Lisa Brown",
                    "property_address": deal.property_address,
                    "purchase_price": 450000 + (i * 50000),
                    "earnest_money": 5000 + (i * 1000),
                    "closing_date": (datetime.now() + timedelta(days=30 + i*10)).isoformat(),
                    "financing_type": "Conventional"
                }
            elif "Listing" in template.name:
                variables = {
                    "seller_name": "Jennifer Garcia",
                    "agent_name": "John Smith",
                    "property_address": deal.property_address,
                    "listing_price": 500000 + (i * 75000),
                    "commission_rate": 0.06,
                    "listing_period": 90
                }
            else:  # Lease agreement
                variables = {
                    "landlord_name": "David Miller",
                    "tenant_name": "Sarah Johnson",
                    "property_address": deal.property_address,
                    "monthly_rent": 2500 + (i * 500),
                    "security_deposit": 5000 + (i * 1000),
                    "lease_term": 12,
                    "start_date": (datetime.now() + timedelta(days=15)).isoformat()
                }

            try:
                contract = Contract(
                    deal_id=deal.id,
                    template_id=template.id,
                    status=["draft", "review", "sent"][i % 3],
                    variables=variables
                )
                self.session.add(contract)
                self.session.commit()
                self.session.refresh(contract)
                contracts.append(contract)
                logger.info(f"Created contract for deal: {deal.title}")
            except IntegrityError:
                self.session.rollback()
                logger.warning(f"Contract already exists for deal: {deal.title}")

        return contracts

    def seed_files(self, deals: List[Deal], users: List[User]) -> List[File]:
        """Seed file uploads for deals."""
        logger.info("Seeding files...")

        files_data = [
            {
                "filename": "property_disclosure.pdf",
                "content_type": "application/pdf",
                "file_size": 1024000,
                "file_type": "document",
                "status": "completed"
            },
            {
                "filename": "financial_preapproval.pdf",
                "content_type": "application/pdf",
                "file_size": 512000,
                "file_type": "document",
                "status": "completed"
            },
            {
                "filename": "property_photos.zip",
                "content_type": "application/zip",
                "file_size": 5120000,
                "file_type": "image",
                "status": "completed"
            },
            {
                "filename": "inspection_report.pdf",
                "content_type": "application/pdf",
                "file_size": 2048000,
                "file_type": "document",
                "status": "processing"
            }
        ]

        files = []
        for i, deal in enumerate(deals[:2]):  # Add files to first 2 deals
            for j, file_data in enumerate(files_data):
                try:
                    file_obj = File(
                        filename=f"{deal.id}_{file_data['filename']}",
                        original_filename=file_data["filename"],
                        content_type=file_data["content_type"],
                        file_size=file_data["file_size"],
                        file_type=file_data["file_type"],
                        status=file_data["status"],
                        storage_path=f"deals/{deal.id}/{file_data['filename']}",
                        owner_id=deal.owner_id,
                        deal_id=deal.id,
                        processing_status="completed" if file_data["status"] == "completed" else "pending"
                    )
                    self.session.add(file_obj)
                    self.session.commit()
                    self.session.refresh(file_obj)
                    files.append(file_obj)
                    logger.info(f"Created file: {file_obj.filename}")
                except IntegrityError:
                    self.session.rollback()
                    logger.warning(f"File already exists: {file_data['filename']}")

        return files

    def seed_ai_agent_data(self, users: List[User], contracts: List[Contract]) -> List[AgentExecution]:
        """Seed AI agent execution data."""
        logger.info("Seeding AI agent execution data...")

        agent_executions = []
        agent_types = ["data_extraction", "contract_generator", "compliance_checker", "signature_tracker", "summary"]

        for i, contract in enumerate(contracts):
            for j, agent_type in enumerate(agent_types[:3]):  # Create executions for first 3 agent types
                try:
                    execution = AgentExecution(
                        agent_type=agent_type,
                        user_id=contract.deal.owner_id,
                        contract_id=contract.id,
                        status="completed" if j < 2 else "running",
                        input_data={"contract_id": contract.id, "template_type": "purchase_agreement"},
                        output_data={"extracted_fields": ["buyer_name", "seller_name", "price"]} if j < 2 else None,
                        execution_time=random.uniform(1.5, 8.5),
                        cost=random.uniform(0.05, 0.25),
                        model_used="qwen-72b",
                        tokens_used=random.randint(500, 2000)
                    )
                    self.session.add(execution)
                    self.session.commit()
                    self.session.refresh(execution)
                    agent_executions.append(execution)
                    logger.info(f"Created agent execution: {agent_type} for contract {contract.id}")
                except IntegrityError:
                    self.session.rollback()
                    logger.warning(f"Agent execution already exists")

        return agent_executions

    def close_session(self):
        """Close database session."""
        self.session.close()


def main():
    """Main seeding function."""
    parser = argparse.ArgumentParser(description="Seed database with integration test data")
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding")
    parser.add_argument("--scenario", default="basic", choices=["basic", "comprehensive", "performance"],
                       help="Seeding scenario")

    args = parser.parse_args()

    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    seeder = DatabaseSeeder(engine)

    try:
        if args.reset:
            seeder.reset_database()

        # Seed data based on scenario
        logger.info(f"Starting {args.scenario} seeding scenario...")

        users = seeder.seed_users()
        templates = seeder.seed_templates()
        deals = seeder.seed_deals(users)
        contracts = seeder.seed_contracts(deals, templates, users)
        files = seeder.seed_files(deals, users)
        agent_executions = seeder.seed_ai_agent_data(users, contracts)

        logger.info("Database seeding completed successfully!")
        logger.info(f"Created {len(users)} users, {len(templates)} templates, {len(deals)} deals")
        logger.info(f"Created {len(contracts)} contracts, {len(files)} files, {len(agent_executions)} agent executions")

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        raise
    finally:
        seeder.close_session()


if __name__ == "__main__":
    main()
