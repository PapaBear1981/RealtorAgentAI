# AI Agent System Setup Guide

## Overview

The AI Agent System has been updated to remove mock/placeholder responses and implement fully functional AI agent capabilities. This guide explains how to configure and test the system.

## Root Cause Analysis

The following issues were identified and fixed:

1. **Backend Agent Execution**: The `_execute_agent_background()` function was returning static mock data instead of calling real AI models
2. **Tool Implementations**: Agent tools contained placeholder implementations with hardcoded responses
3. **Agent Orchestrator**: Workflow execution wasn't properly using CrewAI framework for real AI inference
4. **Model Router Integration**: Needed better error handling and fallback mechanisms

## Changes Made

### 1. Backend Agent Execution (`backend/app/api/v1/ai_agents.py`)
- ✅ Fixed `_execute_agent_background()` to use real CrewAI execution
- ✅ Added proper task creation and agent orchestration
- ✅ Added `/ai-agents/contract-fill` endpoint for frontend integration
- ✅ Added `/ai-agents/document-extract` endpoint for document processing

### 2. Model Router Integration (`backend/app/services/model_router.py`)
- ✅ Enhanced error handling and logging
- ✅ Added fallback response mechanism when all models fail
- ✅ Improved initialization logging to show available models

### 3. Agent Tools (`backend/app/services/agent_tools/`)
- ✅ Replaced mock PDF parsing with real PyPDF2 integration
- ✅ Replaced mock DOCX parsing with real python-docx integration
- ✅ Added real OCR processing with Tesseract integration
- ✅ Integrated with existing template and file services

### 4. Agent Orchestrator (`backend/app/services/agent_orchestrator.py`)
- ✅ Enhanced workflow execution with proper CrewAI integration
- ✅ Added better error handling and result processing
- ✅ Improved cost tracking and agent interaction logging

## Required Configuration

### 1. Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure at least one AI provider:

```bash
# Required: At least one AI provider API key
OPENAI_API_KEY="your-openai-api-key"
ANTHROPIC_API_KEY="your-anthropic-api-key"
OPENROUTER_API_KEY="your-openrouter-api-key"

# Model Router Configuration
MODEL_ROUTER_STRATEGY="cost_optimized"  # or "performance" or "balanced"
MODEL_ROUTER_FALLBACK_ENABLED="true"
MODEL_ROUTER_MAX_RETRIES="3"

# Default Models
DEFAULT_LLM_MODEL="gpt-4o-mini"
```

### 2. Required Dependencies

Install additional Python packages for document processing:

```bash
cd backend
pip install PyPDF2 python-docx pytesseract Pillow
```

### 3. System Dependencies

For OCR functionality, install Tesseract:

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

## Testing the System

### 1. Run the Test Script

```bash
cd backend
python test_ai_agents.py
```

This will test:
- ✅ Environment configuration
- ✅ Model router functionality
- ✅ Agent creation
- ✅ Real AI agent execution

### 2. Expected Output

```
🧪 AI Agent System Test Suite
==================================================
🔍 Checking Environment Configuration...
✅ OpenRouter API key configured
✅ 1 AI provider(s) configured: OpenRouter

🔧 Testing Model Router...
✅ Model Router Response: AI system is working
   Model Used: openrouter/auto
   Provider: OPENROUTER
   Cost: $0.000015
   Processing Time: 1.23s

🤖 Testing Agent Creation...
✅ Created data_extraction agent: Data Extraction Agent
✅ Created contract_generator agent: Contract Generator Agent
✅ Created help_agent agent: Help Agent

🚀 Testing Agent Execution...
✅ Created workflow: test_workflow_001
✅ Workflow Status: COMPLETED
   Execution Time: 3.45s
   Cost: $0.000023
   AI Response: A real estate purchase agreement is a legally binding contract...
✅ Response appears to be real AI-generated content

==================================================
📊 Test Results Summary:
   Model Router: ✅ PASS
   Agent Creation: ✅ PASS
   Agent Execution: ✅ PASS

🎯 Overall: 3/3 tests passed
🎉 All tests passed! AI Agent system is working properly.
```

## API Endpoints

The following AI agent endpoints are now available:

### 1. Contract Filling
```
POST /api/v1/ai-agents/contract-fill
```

Request:
```json
{
  "contract_type": "purchase_agreement",
  "source_data": {...},
  "deal_name": "123 Main St Purchase",
  "template_id": "template_001"
}
```

### 2. Document Extraction
```
POST /api/v1/ai-agents/document-extract
```

Request:
```json
{
  "extracted_data": {...},
  "target_fields": ["buyer_name", "seller_name", "property_address"],
  "source_files": ["file_001", "file_002"]
}
```

### 3. Agent Execution Status
```
GET /api/v1/ai-agents/executions/{execution_id}/status
```

## Troubleshooting

### 1. "No AI provider API keys configured"
- Set at least one API key: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENROUTER_API_KEY`
- OpenRouter is recommended as it provides access to 100+ models

### 2. "All model attempts failed"
- Check API key validity
- Verify internet connectivity
- Check API provider status
- Review logs for specific error messages

### 3. "Document parsing failed"
- Ensure PyPDF2, python-docx, and pytesseract are installed
- For OCR: Install Tesseract system dependency
- Check file permissions and paths

### 4. "Agent execution failed"
- Check CrewAI installation: `pip install crewai`
- Verify model router configuration
- Review agent tool implementations

## Next Steps

1. **Configure API Keys**: Set up at least one AI provider API key
2. **Run Tests**: Execute the test script to verify functionality
3. **Test Frontend**: Use the frontend to test end-to-end workflows
4. **Monitor Costs**: Track AI model usage and costs in production
5. **Scale Up**: Add more AI providers for redundancy and performance

## Support

If you encounter issues:
1. Run the test script to identify specific problems
2. Check the logs for detailed error messages
3. Verify all dependencies are installed
4. Ensure API keys are valid and have sufficient credits
