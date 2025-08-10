#!/usr/bin/env python3
"""
Simple test server for Phase 15B Frontend-Backend Integration Testing
"""

from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Simple test models
class User(BaseModel):
    id: str  # Frontend expects string ID
    email: str
    name: str
    role: str = "agent"
    created_at: str = "2024-01-01T00:00:00Z"
    disabled: bool = False

class Contract(BaseModel):
    id: int
    title: str
    status: str
    created_by: int

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str = "mock-refresh-token"
    token_type: str = "bearer"
    expires_in: int = 3600
    user: User

# Create FastAPI app
app = FastAPI(
    title="RealtorAgentAI Test API",
    description="Test API for Phase 15B Integration Testing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
mock_users = [
    User(id="1", email="agent@test.com", name="Test Agent", role="agent"),
    User(id="2", email="admin@test.com", name="Test Admin", role="admin"),
]

mock_contracts = [
    Contract(id=1, title="Purchase Agreement - 123 Main St", status="draft", created_by=1),
    Contract(id=2, title="Listing Agreement - 456 Oak Ave", status="active", created_by=1),
]

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Test server is running"}

# Authentication endpoints
@app.post("/auth/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Simple mock authentication using OAuth2PasswordRequestForm
    if form_data.username == "agent@test.com" and form_data.password == "password":
        user = mock_users[0]
        return LoginResponse(
            access_token="mock-jwt-token-12345",
            user=user
        )
    elif form_data.username == "admin@test.com" and form_data.password == "password":
        user = mock_users[1]
        return LoginResponse(
            access_token="mock-jwt-token-67890",
            user=user
        )
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auth/me", response_model=User)
async def get_current_user_endpoint():
    # Mock current user endpoint (normally would validate JWT token)
    return mock_users[0]

@app.post("/auth/logout")
async def logout():
    return {"message": "Logged out successfully"}

# User endpoints
@app.get("/users/me", response_model=User)
async def get_current_user():
    # Mock current user (normally would validate JWT token)
    return mock_users[0]

# Contract endpoints
@app.get("/contracts", response_model=List[Contract])
async def get_contracts():
    return mock_contracts

@app.get("/contracts/{contract_id}", response_model=Contract)
async def get_contract(contract_id: int):
    contract = next((c for c in mock_contracts if c.id == contract_id), None)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract

@app.post("/contracts", response_model=Contract)
async def create_contract(contract: Contract):
    # Mock contract creation
    new_contract = Contract(
        id=len(mock_contracts) + 1,
        title=contract.title,
        status="draft",
        created_by=1
    )
    mock_contracts.append(new_contract)
    return new_contract

# File endpoints
@app.get("/files")
async def get_files():
    # Mock file list
    return [
        {
            "id": "1",
            "filename": "Johnson_Property_Disclosure.pdf",
            "size": 2048,
            "status": "processed",
            "uploaded_at": "2024-01-01T10:00:00Z"
        },
        {
            "id": "2",
            "filename": "Johnson_Financial_Info.pdf",
            "size": 1536,
            "status": "processed",
            "uploaded_at": "2024-01-01T10:30:00Z"
        },
        {
            "id": "3",
            "filename": "Property_Inspection_Report.pdf",
            "size": 3072,
            "status": "processed",
            "uploaded_at": "2024-01-01T11:00:00Z"
        }
    ]

@app.post("/files/upload")
async def upload_file():
    # Mock file upload
    return {
        "id": "mock-file-123",
        "filename": "test-document.pdf",
        "size": 1024,
        "status": "uploaded"
    }

# Template endpoints
@app.get("/templates")
async def get_templates():
    return [
        {"id": 1, "name": "Purchase Agreement", "type": "purchase"},
        {"id": 2, "name": "Listing Agreement", "type": "listing"},
    ]

# AI Agent endpoints
@app.post("/ai-agents/extract")
async def extract_data():
    # Mock AI data extraction
    return {
        "status": "completed",
        "extracted_data": {
            "property_address": "123 Main Street",
            "purchase_price": "$500,000",
            "buyer_name": "John Doe"
        }
    }

@app.post("/ai-agents/generate-contract")
async def generate_contract():
    # Mock contract generation
    return {
        "status": "completed",
        "contract_id": 3,
        "message": "Contract generated successfully"
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws/ai-agents/{connection_id}")
async def websocket_endpoint(websocket, connection_id: str):
    await websocket.accept()
    try:
        # Mock WebSocket communication
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "Connected to AI agent updates"
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "echo",
                "message": f"Received: {data}"
            })
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    print("🚀 Starting RealtorAgentAI Test Server for Phase 15B Integration Testing")
    print("📋 Available endpoints:")
    print("   • Health: http://localhost:8000/health")
    print("   • Login: POST http://localhost:8000/auth/login")
    print("   • Contracts: http://localhost:8000/contracts")
    print("   • WebSocket: ws://localhost:8000/ws/ai-agents/{connection_id}")
    print("   • API Docs: http://localhost:8000/docs")
    print()
    print("🔑 Test credentials:")
    print("   • Agent: agent@test.com / password")
    print("   • Admin: admin@test.com / password")

    uvicorn.run(
        "test_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
