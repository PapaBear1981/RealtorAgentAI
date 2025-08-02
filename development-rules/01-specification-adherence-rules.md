# Specification Adherence Rules

## Purpose
These rules ensure strict adherence to the Multi-Agent Real-Estate Contract Platform specification throughout development, preventing scope creep and maintaining project integrity.

## Core Principles

### 1. Specification as Single Source of Truth
- **RULE**: The `RealEstate_MultiAgent_Spec.md` file is the authoritative source for all requirements
- **VALIDATION**: Before implementing any feature, reference the specific section in the spec
- **ENFORCEMENT**: All code changes must map to a specific requirement in the specification

### 2. Feature Implementation Validation
- **BEFORE CODING**: Identify the exact specification section (e.g., "Section 3.2.1 Dashboard")
- **DURING CODING**: Ensure implementation matches specified components, logic, and behavior
- **AFTER CODING**: Verify the feature fulfills the stated requirements completely

### 3. Scope Change Management
- **RULE**: No features outside the specification without explicit approval
- **PROCESS**: 
  1. Document the proposed change
  2. Explain why it's necessary
  3. Get user approval before implementation
  4. Update specification if approved
- **FORBIDDEN**: Adding "nice-to-have" features during development

### 4. Technical Stack Compliance
- **Frontend**: Next.js + Tailwind + shadcn/ui + Zustand + Framer Motion (as specified)
- **Backend**: FastAPI + SQLModel + Alembic (as specified)
- **AI**: CrewAI or LangGraph with specified agents
- **Database**: SQLite (dev), Postgres (staging/prod)
- **RULE**: No technology substitutions without specification update

### 5. Architecture Adherence
- **RULE**: Follow the exact system architecture from Section 2.1
- **VALIDATION**: Ensure all components communicate as specified in Section 2.2
- **ENFORCEMENT**: No architectural changes without updating the specification

## Validation Checklist

### Before Starting Any Feature
- [ ] Identify the specification section
- [ ] Read the complete requirements
- [ ] Understand the acceptance criteria
- [ ] Check for dependencies on other features
- [ ] Verify technical requirements

### During Implementation
- [ ] Reference specification frequently
- [ ] Implement only what's specified
- [ ] Use exact component names and structures
- [ ] Follow specified data models
- [ ] Implement specified endpoints exactly

### After Implementation
- [ ] Compare implementation to specification
- [ ] Test against specified behavior
- [ ] Verify all requirements are met
- [ ] Document any deviations (with approval)

## Specification Sections Reference

### Frontend (Section 3)
- 3.2.1: Dashboard - widgets, components, responsive behavior
- 3.2.2: Document Intake - drag-drop flow, components, edge cases
- 3.2.3: Contract Generator - panels, features, actions
- 3.2.4: Review - redline view, comments, shortcuts
- 3.2.5: Signature Tracker - list, detail, webhooks
- 3.2.6: Help Agent Modal - invoke, context, UI
- 3.2.7: Admin Panel - sections, controls

### Backend (Section 4)
- 4.2: REST Endpoints - exact paths and methods
- 4.3: Models - database schema and relationships
- 4.4: Background Processing - Celery queues and tasks

### AI System (Section 5)
- 5.2: Agents - specific roles and responsibilities
- 5.3: Model Routing - OpenRouter and local support
- 5.4: Prompt Strategy - structured outputs and tools

## Error Prevention

### Common Scope Creep Patterns to Avoid
- Adding extra UI components not in the spec
- Implementing additional API endpoints
- Creating features for "better user experience"
- Adding extra validation rules beyond specification
- Implementing additional integrations

### Specification Interpretation Rules
- **RULE**: When specification is unclear, ask for clarification
- **RULE**: Don't assume requirements - implement exactly as written
- **RULE**: If multiple interpretations exist, choose the simplest one
- **RULE**: Document interpretation decisions for future reference

## Compliance Monitoring

### Regular Checks
- Weekly specification review against implemented features
- Monthly architecture compliance audit
- Continuous validation during code reviews

### Documentation Requirements
- Link each feature to its specification section
- Document any approved deviations
- Maintain traceability matrix (feature → spec section)

## Escalation Process

### When to Escalate
- Specification conflicts or contradictions
- Technical impossibility of specified approach
- Missing requirements for implementation
- Scope change requests

### How to Escalate
1. Document the issue clearly
2. Reference specific specification sections
3. Propose solutions with trade-offs
4. Wait for approval before proceeding
