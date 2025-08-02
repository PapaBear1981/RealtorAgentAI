# Development Rules for Multi-Agent Real-Estate Contract Platform

## Overview
This directory contains comprehensive development rules designed to guide the implementation of the Multi-Agent Real-Estate Contract Platform according to the specification in `RealEstate_MultiAgent_Spec.md`.

## Rules Structure

### 1. [Specification Adherence Rules](./01-specification-adherence-rules.md)
**Purpose**: Ensure strict compliance with the project specification
**Key Areas**:
- Specification as single source of truth
- Feature implementation validation
- Scope change management
- Technical stack compliance
- Architecture adherence

**When to Use**: Before starting any feature, during implementation, and when validating completion

### 2. [Task Management Rules](./02-task-management-rules.md)
**Purpose**: Systematic approach to breaking down and tracking development work
**Key Areas**:
- Task granularity standards (~20 minute tasks)
- Task state management (NOT_STARTED, IN_PROGRESS, COMPLETE, CANCELLED)
- Dependency management
- Progress tracking with Augment's task management tools

**When to Use**: During project planning, daily work organization, and progress tracking

### 3. [Documentation Research Rules](./03-documentation-research-rules.md)
**Purpose**: Ensure use of current best practices and avoid deprecated approaches
**Key Areas**:
- Documentation-first development
- Context7 MCP server usage for latest docs
- Framework-specific research requirements
- Codebase pattern analysis

**When to Use**: Before implementing any new feature, when debugging, and when setting up integrations

### 4. [Development Workflow Rules](./04-development-workflow-rules.md)
**Purpose**: Maintain consistency and quality throughout development
**Key Areas**:
- Quality-first development approach
- Code review processes
- Testing requirements
- Integration and deployment standards

**When to Use**: Throughout the entire development lifecycle

## Quick Reference Guide

### Before Starting Development
1. **Read Specification**: Identify the exact section you're implementing
2. **Research Documentation**: Use Context7 to get latest best practices
3. **Create Tasks**: Break down work into ~20 minute tasks
4. **Plan Quality**: Define testing and review approach

### During Development
1. **Follow Specification**: Implement exactly what's specified
2. **Use Current Practices**: Apply researched best practices
3. **Update Tasks**: Keep task states current
4. **Maintain Quality**: Write tests, review code, document decisions

### After Implementation
1. **Validate Against Spec**: Ensure complete compliance
2. **Complete Testing**: Run all test categories
3. **Update Documentation**: Keep all docs current
4. **Mark Tasks Complete**: Update task management system

## Rule Enforcement Checklist

### Daily Development
- [ ] Reference specification for current work
- [ ] Update task states using Augment tools
- [ ] Research any new implementations
- [ ] Follow code quality standards
- [ ] Write and run tests

### Weekly Review
- [ ] Review specification compliance
- [ ] Audit task progress and dependencies
- [ ] Check for documentation updates
- [ ] Validate quality metrics
- [ ] Plan upcoming work

### Feature Completion
- [ ] Complete specification validation
- [ ] All tasks marked complete
- [ ] Documentation updated
- [ ] Quality standards met
- [ ] Integration tested

## Integration with Augment Tools

### Task Management
```bash
# View current tasks
view_tasklist

# Add new tasks
add_tasks([{
  "name": "Feature Name",
  "description": "Detailed description with spec reference"
}])

# Update task states
update_tasks([{
  "task_id": "task-uuid",
  "state": "COMPLETE"
}])
```

### Documentation Research
```bash
# Research framework documentation
resolve-library-id_Context7("framework-name")
get-library-docs_Context7("/org/project", topic="feature")

# Check existing patterns
codebase-retrieval("implementation pattern")

# Review historical changes
git-commit-retrieval("similar feature")
```

### Code Quality
```bash
# Review code before changes
view("path/to/file", search_query_regex="pattern")

# Make structured edits
str-replace-editor(command="str_replace", ...)

# Run tests
launch-process("npm test", wait=true)
```

## Rule Customization

### Project-Specific Adaptations
These rules are designed for the Multi-Agent Real-Estate Contract Platform but can be adapted for other projects by:
1. Updating specification references
2. Modifying technology stack requirements
3. Adjusting task granularity for project complexity
4. Customizing quality standards for domain requirements

### Rule Evolution
Rules should evolve based on:
- Lessons learned during development
- Changes in technology best practices
- Updates to project requirements
- Team feedback and retrospectives

## Troubleshooting

### When Rules Conflict
1. **Specification takes precedence** over other considerations
2. **Quality standards** cannot be compromised
3. **Documentation research** is mandatory before implementation
4. **Task management** must be maintained for progress tracking

### When Rules Are Unclear
1. Reference the specific rule file for detailed guidance
2. Check the specification for authoritative requirements
3. Research current best practices using Context7
4. Ask for clarification rather than making assumptions

### When Rules Need Updates
1. Document the issue or improvement needed
2. Propose specific changes with rationale
3. Test proposed changes on a small scale
4. Update rules based on validated improvements

## Success Metrics

### Specification Compliance
- 100% of features trace to specification sections
- Zero unauthorized scope additions
- All technical requirements met

### Task Management Effectiveness
- Tasks completed within estimated timeframes
- Clear progress visibility
- Minimal task rework or clarification needed

### Documentation Research Quality
- Current best practices consistently applied
- Minimal deprecated approach usage
- Strong integration with existing patterns

### Development Workflow Quality
- High test coverage (>80%)
- Consistent code quality metrics
- Smooth integration and deployment processes

## Getting Started

1. **Read all rule files** to understand the complete framework
2. **Review the specification** to understand project requirements
3. **Set up Augment tools** for task management and research
4. **Create initial task breakdown** using task management rules
5. **Begin development** following the complete rule framework

Remember: These rules are designed to ensure project success through systematic, quality-focused development. Following them consistently will result in a high-quality implementation that meets all specification requirements.
