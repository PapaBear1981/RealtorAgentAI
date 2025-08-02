# Documentation Research Rules

## Purpose
Mandatory procedures for checking the latest documentation before implementing any new feature or debugging issues, ensuring we use current best practices and avoid deprecated approaches.

## Core Research Principles

### 1. Documentation-First Development
- **RULE**: Always research before implementing
- **SEQUENCE**: Research → Plan → Implement → Validate
- **TOOLS**: Context7 MCP server for latest documentation
- **VALIDATION**: Verify approaches against current best practices

### 2. Research Triggers
**MANDATORY** research before:
- Implementing any new framework feature
- Adding new dependencies or libraries
- Debugging complex issues
- Setting up integrations
- Configuring development tools

### 3. Knowledge Currency
- **ASSUMPTION**: Documentation changes frequently
- **RULE**: Don't rely on cached knowledge
- **VERIFICATION**: Always check for latest updates
- **CURRENCY**: Prefer official docs over tutorials

## Research Workflow

### 1. Pre-Implementation Research
```bash
# STEP 1: Identify what you need to research
# STEP 2: Use Context7 to get latest documentation
resolve-library-id_Context7("framework-name")
get-library-docs_Context7("/org/project", topic="specific-feature")

# STEP 3: Validate approach against specification
# STEP 4: Document findings and approach
```

### 2. Research Documentation Template
```markdown
## Research: [Feature/Issue Name]
**Date**: [Current Date]
**Specification Section**: [Reference]
**Research Question**: [What you need to know]

### Documentation Sources
- Library: [Library Name and Version]
- Documentation: [Specific sections researched]
- Key Findings: [Important discoveries]

### Recommended Approach
- [Approach based on latest documentation]
- [Rationale for chosen method]
- [Alternatives considered]

### Implementation Notes
- [Specific implementation details]
- [Gotchas or important considerations]
- [Testing approach]
```

## Framework-Specific Research Rules

### 1. Next.js Frontend Research
**BEFORE** implementing frontend features:
```bash
# Research Next.js current practices
resolve-library-id_Context7("Next.js")
get-library-docs_Context7("/vercel/next.js", topic="app-router")

# Research shadcn/ui components
resolve-library-id_Context7("shadcn/ui")
get-library-docs_Context7("/shadcn/ui", topic="component-name")

# Research Zustand state management
resolve-library-id_Context7("Zustand")
get-library-docs_Context7("/pmndrs/zustand", topic="state-management")
```

**REQUIRED** research areas:
- App Router vs Pages Router (use App Router per spec)
- Component composition patterns
- State management best practices
- Styling and theming approaches
- Performance optimization techniques

### 2. FastAPI Backend Research
**BEFORE** implementing backend features:
```bash
# Research FastAPI current practices
resolve-library-id_Context7("FastAPI")
get-library-docs_Context7("/tiangolo/fastapi", topic="authentication")

# Research SQLModel patterns
resolve-library-id_Context7("SQLModel")
get-library-docs_Context7("/tiangolo/sqlmodel", topic="relationships")

# Research Celery task management
resolve-library-id_Context7("Celery")
get-library-docs_Context7("/celery/celery", topic="task-routing")
```

**REQUIRED** research areas:
- Authentication and JWT handling
- Database relationships and migrations
- Background task patterns
- API documentation and validation
- Error handling and logging

### 3. AI/ML Framework Research
**BEFORE** implementing AI features:
```bash
# Research CrewAI or LangGraph
resolve-library-id_Context7("CrewAI")
get-library-docs_Context7("/joaomdmoura/crewai", topic="multi-agent")

# Research OpenRouter integration
resolve-library-id_Context7("OpenRouter")
get-library-docs_Context7("/openrouter/openrouter", topic="model-routing")

# Research Ollama local deployment
resolve-library-id_Context7("Ollama")
get-library-docs_Context7("/ollama/ollama", topic="local-models")
```

**REQUIRED** research areas:
- Multi-agent orchestration patterns
- Model routing and fallback strategies
- Prompt engineering best practices
- Tool integration patterns
- Memory and context management

## Codebase Pattern Research

### 1. Existing Pattern Analysis
**BEFORE** creating new functionality:
```bash
# Use codebase-retrieval to find existing patterns
codebase-retrieval("authentication implementation")
codebase-retrieval("API endpoint patterns")
codebase-retrieval("component structure examples")
```

### 2. Historical Context Research
**WHEN** debugging or extending features:
```bash
# Use git-commit-retrieval for historical context
git-commit-retrieval("similar feature implementation")
git-commit-retrieval("authentication changes")
git-commit-retrieval("database migration patterns")
```

### 3. Pattern Consistency Rules
- **RULE**: Follow existing codebase patterns
- **VALIDATION**: Check for similar implementations
- **CONSISTENCY**: Maintain architectural decisions
- **DOCUMENTATION**: Document new patterns for future use

## Research Quality Standards

### 1. Source Verification
- **PRIMARY**: Official documentation first
- **SECONDARY**: Well-maintained community resources
- **AVOID**: Outdated tutorials or blog posts
- **VERIFY**: Check publication dates and version compatibility

### 2. Version Compatibility
- **RULE**: Verify compatibility with project dependencies
- **CHECK**: Package.json and requirements.txt versions
- **VALIDATE**: Test compatibility in development environment
- **DOCUMENT**: Note version-specific considerations

### 3. Best Practice Validation
- **SECURITY**: Research security implications
- **PERFORMANCE**: Check performance considerations
- **MAINTAINABILITY**: Evaluate long-term maintenance
- **SCALABILITY**: Consider scaling implications

## Research Documentation Requirements

### 1. Research Log
Maintain a research log for each major feature:
```markdown
# Research Log: [Feature Name]

## [Date] - Initial Research
- **Question**: [What you researched]
- **Sources**: [Documentation sources]
- **Findings**: [Key discoveries]
- **Decision**: [Chosen approach]

## [Date] - Implementation Issues
- **Problem**: [Issue encountered]
- **Research**: [Additional research done]
- **Solution**: [How it was resolved]
```

### 2. Decision Documentation
Document architectural and implementation decisions:
- **CONTEXT**: Why research was needed
- **OPTIONS**: Alternatives considered
- **DECISION**: Chosen approach and rationale
- **CONSEQUENCES**: Expected outcomes and trade-offs

### 3. Knowledge Sharing
- **TEAM**: Share research findings with team
- **DOCUMENTATION**: Update project documentation
- **PATTERNS**: Document reusable patterns
- **LESSONS**: Capture lessons learned

## Troubleshooting Research

### 1. When Research Conflicts with Specification
- **RULE**: Specification takes precedence
- **PROCESS**: Document the conflict
- **ESCALATION**: Discuss with project owner
- **RESOLUTION**: Update specification if needed

### 2. When Documentation is Unclear
- **MULTIPLE SOURCES**: Check multiple documentation sources
- **COMMUNITY**: Look for community discussions
- **EXPERIMENTATION**: Create small test implementations
- **VALIDATION**: Test approaches thoroughly

### 3. When Best Practices Conflict
- **PRIORITIZE**: Security > Performance > Convenience
- **CONTEXT**: Consider project-specific requirements
- **TRADE-OFFS**: Document decision rationale
- **REVIEW**: Plan for future review and updates

## Research Automation

### 1. Regular Documentation Updates
- **WEEKLY**: Check for major framework updates
- **MONTHLY**: Review dependency updates
- **QUARTERLY**: Audit architectural decisions
- **ANNUALLY**: Major framework migration planning

### 2. Research Templates
Create templates for common research scenarios:
- New feature implementation
- Debugging complex issues
- Performance optimization
- Security enhancement
- Integration setup

### 3. Knowledge Base Maintenance
- **ORGANIZE**: Maintain organized research notes
- **UPDATE**: Keep research current
- **SHARE**: Make findings accessible to team
- **ARCHIVE**: Remove outdated information
