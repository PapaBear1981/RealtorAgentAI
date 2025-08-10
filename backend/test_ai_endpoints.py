#!/usr/bin/env python3
"""
Test script for AI Agent API endpoints.

This script tests the AI agent API endpoints directly without starting the full server.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.api.v1.ai_agents import _execute_agent_background, _execution_storage
from app.services.agent_orchestrator import get_agent_orchestrator, AgentRole
from datetime import datetime


async def test_contract_fill_agent():
    """Test the contract fill functionality."""
    print("🔧 Testing Contract Fill Agent...")

    try:
        # Simulate contract fill request
        execution_id = "test_contract_fill_001"
        agent_role = "contract_generator"
        task_description = """
        Fill a purchase_agreement contract using the provided source data.

        Contract Type: purchase_agreement
        Deal Name: 123 Main St Purchase

        Source Data Available:
        buyer_name, seller_name, property_address, purchase_price

        Please extract relevant information from the source data and generate appropriate
        contract variables and content. Focus on:
        1. Party information (buyers, sellers, agents)
        2. Property details (address, description, features)
        3. Financial terms (price, down payment, financing)
        4. Important dates (closing, contingencies)
        5. Legal terms and conditions

        Provide structured output with extracted variables and confidence scores.
        """

        input_data = {
            "contract_type": "purchase_agreement",
            "source_data": {
                "buyer_name": "John Smith",
                "seller_name": "Jane Doe",
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": "$350,000"
            },
            "deal_name": "123 Main St Purchase",
            "template_id": "default_real_estate"
        }

        # Initialize execution storage
        _execution_storage[execution_id] = {
            "execution_id": execution_id,
            "agent_role": agent_role,
            "task_description": task_description,
            "input_data": input_data,
            "workflow_id": None,
            "user_id": "test_user",
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "result": None,
            "error": None
        }

        # Execute the agent
        await _execute_agent_background(
            execution_id=execution_id,
            agent_role=agent_role,
            task_description=task_description,
            input_data=input_data,
            user_id="test_user"
        )

        # Check the result

        if execution_id in _execution_storage:
            result = _execution_storage[execution_id]
            print(f"✅ Contract Fill Agent Status: {result['status']}")

            if result['status'] == 'completed' and result.get('result'):
                ai_response = result['result'].get('ai_response', '')
                print(f"   AI Response Length: {len(ai_response)} characters")
                print(f"   AI Response Preview: {ai_response[:200]}...")
                print(f"   Execution Time: {result['result'].get('execution_time', 'N/A')}")

                # Check if this looks like real AI content
                if len(ai_response) > 100 and any(keyword in ai_response.lower() for keyword in
                    ['contract', 'agreement', 'buyer', 'seller', 'property', 'purchase']):
                    print("✅ Response appears to be real AI-generated contract content")
                    return True
                else:
                    print("⚠️  Response may not be contract-related content")
                    return False
            else:
                print(f"❌ Agent execution failed or incomplete: {result.get('error', 'Unknown error')}")
                return False
        else:
            print("❌ No execution result found")
            return False

    except Exception as e:
        print(f"❌ Contract Fill Agent Test Failed: {e}")
        return False


async def test_document_extract_agent():
    """Test the document extraction functionality."""
    print("\n📄 Testing Document Extract Agent...")

    try:
        # Simulate document extraction request
        execution_id = "test_document_extract_001"
        agent_role = "data_extraction"
        task_description = """
        Extract and enhance data from the provided documents and existing extracted data.

        Target Fields: buyer_name, seller_name, property_address, purchase_price, closing_date
        Source Files: 2 files

        Existing Extracted Data:
        property_address, purchase_price

        Please analyze the documents and extracted data to:
        1. Identify and extract key entities (parties, properties, financial terms, dates)
        2. Enhance the existing extracted data with additional insights
        3. Validate and improve data quality
        4. Provide confidence scores for extracted information
        5. Structure the data for contract generation

        Focus on real estate contract elements including:
        - Party information (buyers, sellers, agents, attorneys)
        - Property details (address, description, legal description)
        - Financial terms (purchase price, earnest money, financing)
        - Important dates (closing, contingencies, inspections)
        - Legal terms and conditions
        """

        input_data = {
            "extracted_data": {
                "property_address": "123 Main St, Anytown, ST 12345",
                "purchase_price": "$350,000"
            },
            "target_fields": ["buyer_name", "seller_name", "property_address", "purchase_price", "closing_date"],
            "source_files": ["doc_001", "doc_002"]
        }

        # Initialize execution storage
        _execution_storage[execution_id] = {
            "execution_id": execution_id,
            "agent_role": agent_role,
            "task_description": task_description,
            "input_data": input_data,
            "workflow_id": None,
            "user_id": "test_user",
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "result": None,
            "error": None
        }

        # Execute the agent
        await _execute_agent_background(
            execution_id=execution_id,
            agent_role=agent_role,
            task_description=task_description,
            input_data=input_data,
            user_id="test_user"
        )

        # Check the result

        if execution_id in _execution_storage:
            result = _execution_storage[execution_id]
            print(f"✅ Document Extract Agent Status: {result['status']}")

            if result['status'] == 'completed' and result.get('result'):
                ai_response = result['result'].get('ai_response', '')
                print(f"   AI Response Length: {len(ai_response)} characters")
                print(f"   AI Response Preview: {ai_response[:200]}...")
                print(f"   Execution Time: {result['result'].get('execution_time', 'N/A')}")

                # Check if this looks like real AI content
                if len(ai_response) > 100 and any(keyword in ai_response.lower() for keyword in
                    ['extract', 'data', 'property', 'buyer', 'seller', 'analysis']):
                    print("✅ Response appears to be real AI-generated extraction content")
                    return True
                else:
                    print("⚠️  Response may not be extraction-related content")
                    return False
            else:
                print(f"❌ Agent execution failed or incomplete: {result.get('error', 'Unknown error')}")
                return False
        else:
            print("❌ No execution result found")
            return False

    except Exception as e:
        print(f"❌ Document Extract Agent Test Failed: {e}")
        return False


async def test_help_agent():
    """Test the help agent functionality."""
    print("\n❓ Testing Help Agent...")

    try:
        # Simulate help request
        execution_id = "test_help_agent_001"
        agent_role = "help_agent"
        task_description = """
        Please provide guidance on real estate contract contingencies.

        Specifically, explain:
        1. What are contingencies in a real estate purchase agreement?
        2. List the 5 most common types of contingencies
        3. How do contingencies protect buyers and sellers?
        4. What happens if a contingency is not met?

        Provide clear, practical advice that would be helpful for real estate professionals.
        """

        input_data = {
            "topic": "real_estate_contingencies",
            "user_type": "real_estate_professional"
        }

        # Initialize execution storage
        _execution_storage[execution_id] = {
            "execution_id": execution_id,
            "agent_role": agent_role,
            "task_description": task_description,
            "input_data": input_data,
            "workflow_id": None,
            "user_id": "test_user",
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "result": None,
            "error": None
        }

        # Execute the agent
        await _execute_agent_background(
            execution_id=execution_id,
            agent_role=agent_role,
            task_description=task_description,
            input_data=input_data,
            user_id="test_user"
        )

        # Check the result

        if execution_id in _execution_storage:
            result = _execution_storage[execution_id]
            print(f"✅ Help Agent Status: {result['status']}")

            if result['status'] == 'completed' and result.get('result'):
                ai_response = result['result'].get('ai_response', '')
                print(f"   AI Response Length: {len(ai_response)} characters")
                print(f"   AI Response Preview: {ai_response[:200]}...")
                print(f"   Execution Time: {result['result'].get('execution_time', 'N/A')}")

                # Check if this looks like real AI content
                if len(ai_response) > 200 and any(keyword in ai_response.lower() for keyword in
                    ['contingenc', 'real estate', 'buyer', 'seller', 'contract', 'agreement']):
                    print("✅ Response appears to be real AI-generated help content")
                    return True
                else:
                    print("⚠️  Response may not be help-related content")
                    return False
            else:
                print(f"❌ Agent execution failed or incomplete: {result.get('error', 'Unknown error')}")
                return False
        else:
            print("❌ No execution result found")
            return False

    except Exception as e:
        print(f"❌ Help Agent Test Failed: {e}")
        return False


async def main():
    """Run all endpoint tests."""
    print("🧪 AI Agent Endpoint Test Suite")
    print("=" * 50)

    # Run tests
    tests = [
        ("Contract Fill Agent", test_contract_fill_agent),
        ("Document Extract Agent", test_document_extract_agent),
        ("Help Agent", test_help_agent)
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
        print("🎉 All endpoint tests passed! AI Agent endpoints are working properly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration and logs.")


if __name__ == "__main__":
    asyncio.run(main())
