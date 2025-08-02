# Project Structure - Multi-Agent Real-Estate Contract Platform

This document outlines the complete directory structure and organization of the Multi-Agent Real-Estate Contract Platform project.

## 📁 Root Directory Structure

```
RealtorAgentAI/
├── 📄 README.md                           # Project overview and setup
├── 📄 RealEstate_MultiAgent_Spec.md       # Complete specification
├── 📄 MASTER_TASK_LIST.md                 # Project task tracking
├── 📄 PROJECT_STRUCTURE.md                # This file
├── 📄 docker-compose.yml                  # Development environment
├── 📄 .gitignore                          # Git ignore rules
├── 📁 development-rules/                  # Development process rules
├── 📁 backend/                            # FastAPI backend application
├── 📁 frontend/                           # Next.js frontend application
├── 📁 ai-agents/                          # Multi-agent AI system
├── 📁 database/                           # Database files and schemas
├── 📁 docs/                               # Documentation
├── 📁 scripts/                            # Utility scripts
├── 📁 tests/                              # Integration tests
├── 📁 uploads/                            # File uploads (development)
└── 📁 logs/                               # Application logs
```

## 🔧 Backend Structure (`/backend`)

FastAPI application with SQLModel, Celery, and AI integration.

```
backend/
├── 📄 Dockerfile.dev                      # Development Docker configuration
├── 📄 requirements.txt                    # Python dependencies
├── 📄 pyproject.toml                      # Python project configuration
├── 📄 alembic.ini                         # Database migration configuration
├── 📁 app/                                # Main application code
│   ├── 📄 main.py                         # FastAPI application entry point
│   ├── 📄 __init__.py                     # Package initialization
│   ├── 📁 api/                            # API endpoints
│   │   ├── 📄 __init__.py
│   │   ├── 📄 auth.py                     # Authentication endpoints
│   │   ├── 📄 files.py                    # File upload/management
│   │   ├── 📄 contracts.py                # Contract management
│   │   ├── 📄 signatures.py               # Signature tracking
│   │   ├── 📄 admin.py                    # Admin endpoints
│   │   └── 📄 health.py                   # Health check endpoints
│   ├── 📁 core/                           # Core application logic
│   │   ├── 📄 __init__.py
│   │   ├── 📄 config.py                   # Application configuration
│   │   ├── 📄 database.py                 # Database connection
│   │   ├── 📄 security.py                 # Security utilities
│   │   ├── 📄 dependencies.py             # FastAPI dependencies
│   │   └── 📄 exceptions.py               # Custom exceptions
│   ├── 📁 models/                         # SQLModel database models
│   │   ├── 📄 __init__.py
│   │   ├── 📄 user.py                     # User models
│   │   ├── 📄 deal.py                     # Deal models
│   │   ├── 📄 contract.py                 # Contract models
│   │   ├── 📄 signature.py                # Signature models
│   │   ├── 📄 upload.py                   # File upload models
│   │   └── 📄 audit.py                    # Audit trail models
│   ├── 📁 services/                       # Business logic services
│   │   ├── 📄 __init__.py
│   │   ├── 📄 auth_service.py             # Authentication service
│   │   ├── 📄 file_service.py             # File management service
│   │   ├── 📄 contract_service.py         # Contract business logic
│   │   ├── 📄 signature_service.py        # Signature management
│   │   └── 📄 storage_service.py          # S3/MinIO storage service
│   ├── 📁 agents/                         # AI agent integration
│   │   ├── 📄 __init__.py
│   │   ├── 📄 orchestrator.py             # Agent orchestration
│   │   ├── 📄 extraction_agent.py         # Data extraction agent
│   │   ├── 📄 generator_agent.py          # Contract generator agent
│   │   ├── 📄 compliance_agent.py         # Compliance checker agent
│   │   └── 📄 help_agent.py               # Help agent
│   ├── 📁 parsers/                        # Document parsing utilities
│   │   ├── 📄 __init__.py
│   │   ├── 📄 pdf_parser.py               # PDF document parser
│   │   ├── 📄 docx_parser.py              # DOCX document parser
│   │   ├── 📄 ocr_parser.py               # OCR processing
│   │   └── 📄 base_parser.py              # Base parser interface
│   ├── 📁 templates/                      # Contract templates
│   │   ├── 📄 __init__.py
│   │   ├── 📄 template_engine.py          # Template processing
│   │   └── 📁 contracts/                  # Template files
│   └── 📁 celery_tasks/                   # Background tasks
│       ├── 📄 __init__.py
│       ├── 📄 celery_app.py               # Celery configuration
│       ├── 📄 document_tasks.py           # Document processing tasks
│       ├── 📄 ai_tasks.py                 # AI processing tasks
│       └── 📄 notification_tasks.py       # Notification tasks
├── 📁 alembic/                            # Database migrations
│   ├── 📄 env.py                          # Alembic environment
│   ├── 📄 script.py.mako                  # Migration template
│   └── 📁 versions/                       # Migration files
└── 📁 tests/                              # Backend tests
    ├── 📄 __init__.py
    ├── 📄 conftest.py                     # Test configuration
    ├── 📁 api/                            # API endpoint tests
    ├── 📁 services/                       # Service tests
    └── 📁 models/                         # Model tests
```

## 🎨 Frontend Structure (`/frontend`)

Next.js application with TypeScript, Tailwind CSS, and shadcn/ui.

```
frontend/
├── 📄 Dockerfile.dev                      # Development Docker configuration
├── 📄 package.json                        # Node.js dependencies
├── 📄 package-lock.json                   # Dependency lock file
├── 📄 next.config.js                      # Next.js configuration
├── 📄 tailwind.config.js                  # Tailwind CSS configuration
├── 📄 tsconfig.json                       # TypeScript configuration
├── 📄 postcss.config.js                   # PostCSS configuration
├── 📄 .eslintrc.json                      # ESLint configuration
├── 📄 prettier.config.js                  # Prettier configuration
├── 📁 public/                             # Static assets
│   ├── 📄 favicon.ico
│   └── 📁 images/
├── 📁 src/                                # Source code
│   ├── 📁 app/                            # Next.js App Router
│   │   ├── 📄 layout.tsx                  # Root layout
│   │   ├── 📄 page.tsx                    # Home page
│   │   ├── 📄 globals.css                 # Global styles
│   │   ├── 📁 dashboard/                  # Dashboard pages
│   │   ├── 📁 intake/                     # Document intake pages
│   │   ├── 📁 generator/                  # Contract generator pages
│   │   ├── 📁 review/                     # Review pages
│   │   ├── 📁 signatures/                 # Signature tracking pages
│   │   ├── 📁 admin/                      # Admin pages
│   │   └── 📁 api/                        # API routes (if needed)
│   ├── 📁 components/                     # React components
│   │   ├── 📁 ui/                         # shadcn/ui components
│   │   │   ├── 📄 button.tsx
│   │   │   ├── 📄 card.tsx
│   │   │   ├── 📄 dialog.tsx
│   │   │   ├── 📄 form.tsx
│   │   │   ├── 📄 input.tsx
│   │   │   ├── 📄 table.tsx
│   │   │   └── 📄 ...
│   │   ├── 📁 dashboard/                  # Dashboard components
│   │   │   ├── 📄 DealWidget.tsx
│   │   │   ├── 📄 SignatureWidget.tsx
│   │   │   ├── 📄 ComplianceWidget.tsx
│   │   │   └── 📄 RecentUploadsWidget.tsx
│   │   ├── 📁 intake/                     # Document intake components
│   │   │   ├── 📄 FileDropzone.tsx
│   │   │   ├── 📄 PreviewPanel.tsx
│   │   │   └── 📄 TypeSelector.tsx
│   │   ├── 📁 generator/                  # Contract generator components
│   │   │   ├── 📄 TemplatePanel.tsx
│   │   │   ├── 📄 VariableForm.tsx
│   │   │   ├── 📄 LivePreview.tsx
│   │   │   └── 📄 HintsPanel.tsx
│   │   ├── 📁 review/                     # Review components
│   │   │   ├── 📄 RedlineView.tsx
│   │   │   ├── 📄 CommentThread.tsx
│   │   │   └── 📄 ApprovalButtons.tsx
│   │   ├── 📁 signatures/                 # Signature components
│   │   │   ├── 📄 PartyList.tsx
│   │   │   ├── 📄 StatusTracker.tsx
│   │   │   └── 📄 AuditTrail.tsx
│   │   ├── 📁 help/                       # Help agent components
│   │   │   ├── 📄 HelpModal.tsx
│   │   │   ├── 📄 ChatInterface.tsx
│   │   │   └── 📄 QuickActions.tsx
│   │   └── 📁 admin/                      # Admin components
│   │       ├── 📄 UserManagement.tsx
│   │       ├── 📄 TemplateManager.tsx
│   │       ├── 📄 ModelConfig.tsx
│   │       └── 📄 AuditSearch.tsx
│   ├── 📁 lib/                            # Utility libraries
│   │   ├── 📄 api.ts                      # API client
│   │   ├── 📄 auth.ts                     # Authentication utilities
│   │   ├── 📄 utils.ts                    # General utilities
│   │   └── 📄 validations.ts              # Form validations
│   ├── 📁 hooks/                          # Custom React hooks
│   │   ├── 📄 useAuth.ts                  # Authentication hook
│   │   ├── 📄 useApi.ts                   # API hooks
│   │   └── 📄 useLocalStorage.ts          # Local storage hook
│   ├── 📁 stores/                         # Zustand stores
│   │   ├── 📄 authStore.ts                # Authentication state
│   │   ├── 📄 dealStore.ts                # Deal state
│   │   └── 📄 uiStore.ts                  # UI state
│   ├── 📁 types/                          # TypeScript type definitions
│   │   ├── 📄 api.ts                      # API types
│   │   ├── 📄 auth.ts                     # Authentication types
│   │   ├── 📄 contract.ts                 # Contract types
│   │   └── 📄 common.ts                   # Common types
│   └── 📁 styles/                         # Additional styles
│       └── 📄 components.css              # Component-specific styles
└── 📁 __tests__/                          # Frontend tests
    ├── 📄 setup.ts                        # Test setup
    ├── 📁 components/                     # Component tests
    └── 📁 pages/                          # Page tests
```

## 🤖 AI Agents Structure (`/ai-agents`)

Multi-agent system with CrewAI/LangGraph orchestration.

```
ai-agents/
├── 📄 requirements.txt                    # AI-specific dependencies
├── 📄 config.py                          # AI system configuration
├── 📁 orchestrator/                      # Agent orchestration
│   ├── 📄 __init__.py
│   ├── 📄 crew_manager.py                # CrewAI orchestrator
│   ├── 📄 workflow.py                    # Workflow definitions
│   └── 📄 router.py                      # Model routing
├── 📁 agents/                            # Individual agents
│   ├── 📄 __init__.py
│   ├── 📄 base_agent.py                  # Base agent class
│   ├── 📄 extraction_agent.py            # Data extraction
│   ├── 📄 generator_agent.py             # Contract generation
│   ├── 📄 compliance_agent.py            # Error/compliance checking
│   ├── 📄 signature_agent.py             # Signature tracking
│   ├── 📄 summary_agent.py               # Summarization
│   └── 📄 help_agent.py                  # Contextual help
├── 📁 tools/                             # Agent tools
│   ├── 📄 __init__.py
│   ├── 📄 file_tools.py                  # File processing tools
│   ├── 📄 database_tools.py              # Database interaction tools
│   ├── 📄 validation_tools.py            # Validation tools
│   └── 📄 api_tools.py                   # External API tools
├── 📁 prompts/                           # Prompt templates
│   ├── 📄 __init__.py
│   ├── 📄 extraction_prompts.py          # Data extraction prompts
│   ├── 📄 generation_prompts.py          # Contract generation prompts
│   ├── 📄 compliance_prompts.py          # Compliance checking prompts
│   └── 📄 help_prompts.py                # Help agent prompts
├── 📁 memory/                            # Agent memory management
│   ├── 📄 __init__.py
│   ├── 📄 vector_store.py                # Vector database
│   ├── 📄 conversation_memory.py         # Conversation history
│   └── 📄 context_manager.py             # Context management
└── 📁 tests/                             # AI system tests
    ├── 📄 __init__.py
    ├── 📁 agents/                        # Agent tests
    ├── 📁 tools/                         # Tool tests
    └── 📁 integration/                   # Integration tests
```

## 📚 Documentation Structure (`/docs`)

Comprehensive project documentation.

```
docs/
├── 📁 api/                               # API documentation
│   ├── 📄 README.md                      # API overview
│   ├── 📄 authentication.md              # Auth endpoints
│   ├── 📄 contracts.md                   # Contract endpoints
│   └── 📄 signatures.md                  # Signature endpoints
├── 📁 components/                        # Component documentation
│   ├── 📄 README.md                      # Component overview
│   ├── 📄 dashboard.md                   # Dashboard components
│   ├── 📄 intake.md                      # Intake components
│   └── 📄 generator.md                   # Generator components
├── 📁 deployment/                        # Deployment guides
│   ├── 📄 README.md                      # Deployment overview
│   ├── 📄 docker.md                      # Docker deployment
│   ├── 📄 kubernetes.md                  # Kubernetes deployment
│   └── 📄 production.md                  # Production setup
└── 📁 architecture/                      # Architecture documentation
    ├── 📄 README.md                      # Architecture overview
    ├── 📄 database-schema.md             # Database design
    ├── 📄 ai-system.md                   # AI system architecture
    └── 📄 security.md                    # Security architecture
```

## 🔧 Configuration Files

### Root Level Configuration
- **docker-compose.yml**: Development environment orchestration
- **.gitignore**: Git ignore patterns for all project types
- **README.md**: Project overview and quick start guide

### Backend Configuration
- **requirements.txt**: Python dependencies
- **Dockerfile.dev**: Development container configuration
- **alembic.ini**: Database migration configuration
- **pyproject.toml**: Python project metadata and tools

### Frontend Configuration
- **package.json**: Node.js dependencies and scripts
- **next.config.js**: Next.js framework configuration
- **tailwind.config.js**: Tailwind CSS customization
- **tsconfig.json**: TypeScript compiler options

## 🚀 Development Workflow

### 1. Environment Setup
```bash
# Start development environment
docker-compose up -d

# Install dependencies (if running locally)
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

### 2. Development Commands
```bash
# Backend development
cd backend && fastapi dev app/main.py

# Frontend development
cd frontend && npm run dev

# Run tests
cd backend && pytest
cd frontend && npm test
```

### 3. Database Management
```bash
# Create migration
cd backend && alembic revision --autogenerate -m "description"

# Apply migrations
cd backend && alembic upgrade head
```

## 📝 Notes

- **SQLite**: Used for development database (file-based)
- **PostgreSQL**: Used for staging/production environments
- **Redis**: Used for caching and Celery message broker
- **MinIO**: S3-compatible object storage for development
- **Docker**: Containerized development environment
- **Hot Reload**: Both frontend and backend support live reloading

This structure follows the specification requirements and provides a solid foundation for systematic development following our established development rules.
