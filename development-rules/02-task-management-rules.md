# Task Management Rules

## Purpose
Detailed procedures for creating, maintaining, and updating development task lists using Augment's task management tools to ensure systematic progress tracking and efficient workflow management.

## Core Task Management Principles

### 1. Task Granularity Standard
- **RULE**: Each task represents ~20 minutes of professional development work
- **TOO GRANULAR**: "Add import statement", "Fix typo"
- **TOO BROAD**: "Implement entire frontend", "Build complete API"
- **JUST RIGHT**: "Create Dashboard component with widgets", "Implement JWT authentication middleware"

### 2. Task State Management
- **NOT_STARTED** `[ ]`: Tasks not yet begun
- **IN_PROGRESS** `[/]`: Currently active tasks
- **COMPLETE** `[x]`: Finished and verified tasks
- **CANCELLED** `[-]`: No longer relevant tasks

### 3. Task Hierarchy Rules
- **Root Task**: Overall project or major feature
- **Sub-tasks**: Specific implementation steps
- **Maximum Depth**: 3 levels (Root → Feature → Implementation)

## Task Creation Process

### 1. Specification Analysis
**BEFORE** creating tasks:
1. Read the complete specification section
2. Identify all components, endpoints, and features
3. Understand dependencies between features
4. Map to technical implementation steps

### 2. Task Breakdown Template
```
Feature: [Specification Section] - [Feature Name]
├── Setup and Configuration
├── Core Implementation
├── Integration Points
├── Testing and Validation
└── Documentation
```

### 3. Task Naming Convention
- **Format**: `[Component/Area]: [Action] - [Specific Detail]`
- **Examples**:
  - `Frontend: Create Dashboard component with widgets`
  - `Backend: Implement JWT authentication middleware`
  - `AI: Setup Data Extraction Agent with confidence scoring`
  - `Database: Create User and Deal models with relationships`

## Task Management Workflow

### 1. Initial Project Setup
```bash
# Use add_tasks to create the project structure
add_tasks([
  {
    "name": "Project Setup and Infrastructure",
    "description": "Initialize development environment and core infrastructure"
  },
  {
    "name": "Frontend Development",
    "description": "Implement Next.js frontend with all specified components"
  },
  {
    "name": "Backend Development", 
    "description": "Build FastAPI backend with all specified endpoints"
  },
  {
    "name": "AI Agent System",
    "description": "Implement multi-agent system with CrewAI/LangGraph"
  }
])
```

### 2. Feature Breakdown Process
For each major feature (e.g., Dashboard):
1. Create parent task from specification section
2. Break down into implementation sub-tasks
3. Identify dependencies and order tasks
4. Estimate effort (aim for ~20 minute tasks)

### 3. Task State Updates
**RULE**: Use batch updates for efficiency
```bash
# When starting new work
update_tasks([
  {"task_id": "previous-task-id", "state": "COMPLETE"},
  {"task_id": "current-task-id", "state": "IN_PROGRESS"}
])
```

### 4. Progress Tracking
- **Daily**: Review IN_PROGRESS tasks
- **Weekly**: Update task states and add new tasks as needed
- **Per Feature**: Mark parent task complete when all sub-tasks done

## Task Categories and Templates

### 1. Frontend Tasks Template
```
Frontend: [Component Name]
├── Create component structure and basic layout
├── Implement core functionality and state management
├── Add responsive design and styling
├── Integrate with backend APIs
├── Add error handling and loading states
└── Write component tests
```

### 2. Backend Tasks Template
```
Backend: [Feature Name]
├── Define data models and schemas
├── Implement API endpoints
├── Add authentication and authorization
├── Create background task handlers
├── Add validation and error handling
└── Write API tests
```

### 3. AI Agent Tasks Template
```
AI: [Agent Name]
├── Define agent role and capabilities
├── Implement core agent logic
├── Create tools and integrations
├── Add prompt templates and validation
├── Integrate with orchestrator
└── Test agent responses
```

## Dependency Management

### 1. Dependency Identification
- **RULE**: Identify dependencies before creating tasks
- **MARK**: Use task descriptions to note dependencies
- **ORDER**: Sequence tasks based on dependencies

### 2. Dependency Types
- **Technical**: Database models before API endpoints
- **Feature**: Authentication before protected routes
- **Integration**: Backend endpoints before frontend integration

### 3. Blocking Task Management
- **RULE**: Mark blocked tasks clearly in descriptions
- **PROCESS**: Don't start blocked tasks until dependencies complete
- **COMMUNICATION**: Update task descriptions when blockers resolve

## Task Quality Standards

### 1. Task Description Requirements
- **WHAT**: Clear description of what needs to be done
- **WHY**: Reference to specification section
- **HOW**: Brief technical approach if complex
- **DONE**: Clear completion criteria

### 2. Task Validation Checklist
Before marking a task COMPLETE:
- [ ] Implementation matches specification
- [ ] Code follows project standards
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Integration points work correctly

### 3. Task Review Process
- **SELF-REVIEW**: Check task completion against criteria
- **SPECIFICATION**: Verify against original requirements
- **TESTING**: Ensure functionality works as expected

## Advanced Task Management

### 1. Epic Management
For large features spanning multiple sessions:
- Create epic-level tasks for major specification sections
- Break into smaller tasks as work progresses
- Use parent-child relationships to maintain hierarchy

### 2. Sprint Planning
- **Weekly**: Plan tasks for the upcoming week
- **CAPACITY**: Consider available time and complexity
- **PRIORITIES**: Focus on specification order and dependencies

### 3. Task Refinement
- **ONGOING**: Refine tasks as understanding improves
- **SPLIT**: Break down tasks that become too large
- **MERGE**: Combine tasks that are too small

## Troubleshooting Task Management

### 1. Common Issues
- **Tasks too large**: Break into smaller sub-tasks
- **Tasks too small**: Combine related micro-tasks
- **Unclear requirements**: Reference specification and ask for clarification
- **Blocked progress**: Identify and resolve dependencies

### 2. Task Recovery
When tasks become stale or unclear:
1. Review original specification section
2. Assess current implementation state
3. Update task description with current context
4. Break down remaining work into clear steps

### 3. Progress Stalls
When progress stops:
1. Review task list for blockers
2. Identify missing dependencies
3. Re-prioritize based on current state
4. Ask for guidance if stuck
