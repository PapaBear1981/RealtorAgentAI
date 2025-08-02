# Development Workflow Rules

## Purpose
Guidelines for maintaining consistency and quality throughout the development process, including code review checkpoints, testing requirements, and workflow standards.

## Core Workflow Principles

### 1. Quality-First Development
- **RULE**: Quality over speed - build it right the first time
- **VALIDATION**: Every feature must meet quality standards before completion
- **TESTING**: Comprehensive testing is mandatory, not optional
- **REVIEW**: All code changes require self-review against standards

### 2. Incremental Development
- **APPROACH**: Build features incrementally with frequent validation
- **FEEDBACK**: Validate each increment against specification
- **ITERATION**: Refine based on testing and review feedback
- **INTEGRATION**: Integrate frequently to catch issues early

### 3. Documentation-Driven Development
- **SEQUENCE**: Research → Document → Implement → Test → Review
- **TRACEABILITY**: Every feature traces back to specification
- **KNOWLEDGE**: Capture decisions and rationale
- **MAINTENANCE**: Keep documentation current with implementation

## Pre-Development Checklist

### 1. Before Starting Any Feature
- [ ] Read and understand specification section completely
- [ ] Research current best practices using Context7
- [ ] Check existing codebase patterns with codebase-retrieval
- [ ] Create or update task list with specific implementation steps
- [ ] Identify dependencies and integration points
- [ ] Plan testing approach and acceptance criteria

### 2. Environment Preparation
- [ ] Development environment is clean and up-to-date
- [ ] All dependencies are current and compatible
- [ ] Database is in known good state
- [ ] Testing framework is configured and working
- [ ] Documentation tools are available

### 3. Code Quality Setup
- [ ] Linting rules are configured and active
- [ ] Type checking is enabled (TypeScript/Python typing)
- [ ] Code formatting is consistent
- [ ] Git hooks are configured for quality checks

## Development Process

### 1. Implementation Workflow
```
1. Research Phase
   ├── Use Context7 for latest documentation
   ├── Check codebase patterns with codebase-retrieval
   └── Document approach and decisions

2. Planning Phase
   ├── Break down feature into tasks (~20 min each)
   ├── Identify integration points and dependencies
   └── Plan testing strategy

3. Implementation Phase
   ├── Write failing tests first (TDD when appropriate)
   ├── Implement minimum viable feature
   ├── Refactor for quality and maintainability
   └── Ensure all tests pass

4. Integration Phase
   ├── Test integration points
   ├── Validate against specification
   └── Update documentation

5. Review Phase
   ├── Self-review against quality standards
   ├── Run full test suite
   └── Mark task complete
```

### 2. Code Quality Standards

#### Frontend Code Quality
- **Components**: Single responsibility, reusable, well-typed
- **State**: Minimal, predictable, well-structured
- **Styling**: Consistent with design system, responsive
- **Performance**: Optimized rendering, lazy loading where appropriate
- **Accessibility**: WCAG compliant, keyboard navigation

#### Backend Code Quality
- **APIs**: RESTful, well-documented, consistent error handling
- **Models**: Properly typed, validated, with clear relationships
- **Security**: Authentication, authorization, input validation
- **Performance**: Efficient queries, proper indexing, caching
- **Monitoring**: Logging, metrics, error tracking

#### AI/ML Code Quality
- **Agents**: Clear roles, well-defined tools, proper error handling
- **Prompts**: Versioned, tested, with fallback strategies
- **Models**: Proper routing, cost management, performance monitoring
- **Integration**: Robust error handling, timeout management

### 3. Testing Requirements

#### Test Categories (All Required)
- **Unit Tests**: Individual functions and components
- **Integration Tests**: API endpoints and database interactions
- **Component Tests**: Frontend component behavior
- **End-to-End Tests**: Complete user workflows
- **Performance Tests**: Load and response time validation

#### Test Quality Standards
- **Coverage**: Minimum 80% code coverage
- **Scenarios**: Happy path, error cases, edge cases
- **Data**: Realistic test data, proper fixtures
- **Isolation**: Tests don't depend on each other
- **Speed**: Fast execution, parallel where possible

#### Test Documentation
- **Purpose**: Clear test descriptions
- **Setup**: Document test environment requirements
- **Data**: Explain test data and fixtures
- **Assertions**: Clear, meaningful assertions

## Code Review Process

### 1. Self-Review Checklist
Before marking any task complete:
- [ ] Code follows project conventions and standards
- [ ] Implementation matches specification exactly
- [ ] All tests are written and passing
- [ ] Error handling is comprehensive
- [ ] Performance considerations are addressed
- [ ] Security implications are considered
- [ ] Documentation is updated
- [ ] Integration points are tested

### 2. Code Review Criteria

#### Functionality Review
- [ ] Feature works as specified
- [ ] All edge cases are handled
- [ ] Error conditions are managed gracefully
- [ ] Performance is acceptable
- [ ] Security vulnerabilities are addressed

#### Code Quality Review
- [ ] Code is readable and maintainable
- [ ] Follows established patterns and conventions
- [ ] Proper separation of concerns
- [ ] Appropriate abstraction levels
- [ ] No code duplication without justification

#### Testing Review
- [ ] Comprehensive test coverage
- [ ] Tests are meaningful and valuable
- [ ] Test data is appropriate
- [ ] Tests run reliably
- [ ] Performance tests validate requirements

### 3. Review Documentation
Document review findings:
```markdown
## Code Review: [Feature Name]
**Date**: [Review Date]
**Reviewer**: [Your Name]
**Specification**: [Section Reference]

### Functionality ✅/❌
- [ ] Meets specification requirements
- [ ] Handles error cases appropriately
- [ ] Performance is acceptable

### Code Quality ✅/❌
- [ ] Follows project conventions
- [ ] Maintainable and readable
- [ ] Proper abstractions

### Testing ✅/❌
- [ ] Comprehensive coverage
- [ ] Meaningful test cases
- [ ] All tests passing

### Issues Found
- [List any issues that need addressing]

### Recommendations
- [Suggestions for improvement]
```

## Integration and Deployment

### 1. Integration Checklist
Before integrating features:
- [ ] All tests pass locally
- [ ] Integration points are tested
- [ ] Database migrations are tested
- [ ] API contracts are validated
- [ ] Frontend-backend integration works
- [ ] Error handling is end-to-end tested

### 2. Deployment Preparation
- [ ] Environment configurations are correct
- [ ] Database migrations are ready
- [ ] Dependencies are documented
- [ ] Rollback plan is prepared
- [ ] Monitoring is configured

### 3. Post-Deployment Validation
- [ ] All functionality works in target environment
- [ ] Performance meets requirements
- [ ] Error rates are acceptable
- [ ] Monitoring shows healthy metrics
- [ ] User acceptance criteria are met

## Quality Assurance

### 1. Continuous Quality Monitoring
- **Daily**: Run full test suite
- **Weekly**: Review code quality metrics
- **Monthly**: Audit against specification compliance
- **Quarterly**: Architecture and performance review

### 2. Quality Metrics
Track and maintain:
- **Test Coverage**: >80% for all components
- **Performance**: API response times <500ms
- **Reliability**: >99% uptime in development
- **Security**: Zero high-severity vulnerabilities
- **Maintainability**: Code complexity within acceptable ranges

### 3. Quality Improvement
- **Retrospectives**: Regular review of quality issues
- **Process Improvement**: Update rules based on lessons learned
- **Tool Enhancement**: Improve development and testing tools
- **Training**: Stay current with best practices

## Troubleshooting Workflow Issues

### 1. When Quality Standards Aren't Met
- **STOP**: Don't proceed until standards are met
- **ANALYZE**: Identify root cause of quality issues
- **FIX**: Address underlying problems
- **VALIDATE**: Ensure fixes meet standards
- **DOCUMENT**: Update processes to prevent recurrence

### 2. When Tests Fail
- **INVESTIGATE**: Understand why tests are failing
- **FIX**: Address the root cause, not just symptoms
- **VALIDATE**: Ensure fix doesn't break other functionality
- **IMPROVE**: Strengthen tests to catch similar issues

### 3. When Integration Issues Occur
- **ISOLATE**: Identify the specific integration point
- **TEST**: Create focused integration tests
- **FIX**: Address integration problems systematically
- **VALIDATE**: Test end-to-end functionality
- **DOCUMENT**: Update integration documentation

## Workflow Optimization

### 1. Automation Opportunities
- **Testing**: Automated test execution and reporting
- **Quality**: Automated code quality checks
- **Deployment**: Automated deployment pipelines
- **Monitoring**: Automated alerting and reporting

### 2. Process Improvement
- **Feedback**: Regular workflow retrospectives
- **Metrics**: Track workflow efficiency
- **Tools**: Invest in better development tools
- **Training**: Continuous learning and improvement

### 3. Knowledge Management
- **Documentation**: Keep workflow documentation current
- **Sharing**: Share lessons learned and best practices
- **Templates**: Create reusable workflow templates
- **Standards**: Evolve standards based on experience
