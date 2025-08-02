# Task List Verification Rules

## Purpose
Automated verification system to ensure the MASTER_TASK_LIST.md is properly updated before git commits, maintaining compliance with our task management rules and preventing incomplete progress tracking.

## Core Verification Principles

### 1. Mandatory Task List Updates
- **RULE**: All code changes must be accompanied by task list updates
- **ENFORCEMENT**: Pre-commit hook blocks commits without proper task list updates
- **RATIONALE**: Maintains accurate progress tracking and project visibility

### 2. Verification Triggers
- **AUTOMATIC**: Pre-commit hook runs on every `git commit`
- **MANUAL**: Can be run independently with `python scripts/verify_tasklist.py`
- **BYPASS**: Available with `git commit --no-verify` (strongly discouraged)

### 3. Quality Gates
- **ERRORS**: Block commits and must be fixed
- **WARNINGS**: Allow commits but should be addressed
- **CRITICAL**: System errors that prevent verification

## Verification Checks

### 1. File Existence Check
**Purpose**: Ensure MASTER_TASK_LIST.md exists
**Failure**: Critical error - blocks commit
**Fix**: Ensure the task list file exists in the repository root

### 2. File Structure Check
**Purpose**: Verify required sections are present
**Required Sections**:
- Task Management Rules Reference
- Current Task Status Overview
- Completion Metrics
- Next Immediate Steps
- Recent Accomplishments

**Failure**: Error - blocks commit
**Fix**: Add missing sections to the task list

### 3. Last Updated Check
**Purpose**: Ensure the "Last Updated" field reflects recent changes
**Pattern**: `**Last Updated**: YYYY-MM-DD`
**Failure**: Warning - allows commit
**Fix**: Update the date to today's date

### 4. Completion Metrics Check
**Purpose**: Verify task counts are accurate and add up correctly
**Metrics Verified**:
- Total Tasks
- Completed Tasks
- In Progress Tasks
- Not Started Tasks
- Cancelled Tasks

**Failure**: Error - blocks commit
**Fix**: Update metrics to reflect actual task states

### 5. Task States Check
**Purpose**: Verify task checkboxes are properly formatted
**Valid States**:
- `[ ]` - NOT_STARTED
- `[/]` - IN_PROGRESS
- `[x]` - COMPLETE
- `[-]` - CANCELLED

**Failure**: Warning - allows commit
**Fix**: Ensure all task checkboxes use correct formatting

### 6. Recent Accomplishments Check
**Purpose**: Verify recent work is documented
**Requirements**:
- Recent Accomplishments section exists
- Contains commit references (format: `\`abc1234\``)

**Failure**: Warning - allows commit
**Fix**: Add recent accomplishments with commit hashes

### 7. Staged Changes Check
**Purpose**: Ensure task list is staged when code changes are staged
**Logic**: If code files are staged, task list must also be staged
**Code Extensions**: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.vue`, etc.
**Config Files**: `docker-compose.yml`, `Dockerfile`, `package.json`, etc.

**Failure**: Error - blocks commit
**Fix**: Stage the updated task list file with `git add MASTER_TASK_LIST.md`

## Installation and Setup

### 1. Install Git Hooks
```bash
# Run the installation script
python scripts/install_git_hooks.py
```

### 2. Manual Verification
```bash
# Run verification manually
python scripts/verify_tasklist.py
```

### 3. Bypass Hook (Emergency Only)
```bash
# Bypass verification (strongly discouraged)
git commit --no-verify -m "Emergency commit"
```

## Verification Workflow

### 1. Normal Development Flow
```bash
# 1. Make code changes
# 2. Update task progress using Augment tools
update_tasks([{"task_id": "task-uuid", "state": "COMPLETE"}])

# 3. Update MASTER_TASK_LIST.md manually if needed
# 4. Stage all changes
git add .

# 5. Commit (verification runs automatically)
git commit -m "Your commit message"
```

### 2. When Verification Fails
```bash
# 1. Review the error messages
# 2. Fix the identified issues
# 3. Stage the updated task list
git add MASTER_TASK_LIST.md

# 4. Retry the commit
git commit -m "Your commit message"
```

## Error Resolution Guide

### Common Errors and Fixes

#### "Code changes are staged but MASTER_TASK_LIST.md is not staged"
**Cause**: You've made code changes but haven't updated the task list
**Fix**:
1. Update your task progress using Augment tools
2. Update completion metrics in MASTER_TASK_LIST.md
3. Add recent accomplishments
4. Stage the task list: `git add MASTER_TASK_LIST.md`

#### "Completion metrics don't add up"
**Cause**: Task counts don't match the total
**Fix**:
1. Count actual tasks in each state
2. Update the metrics section with correct numbers
3. Ensure: Total = Completed + In Progress + Not Started + Cancelled

#### "Missing required sections"
**Cause**: Task list is missing essential sections
**Fix**:
1. Add the missing sections to MASTER_TASK_LIST.md
2. Follow the template structure from the original file

#### "No recent commit references found"
**Cause**: Recent Accomplishments section lacks commit hashes
**Fix**:
1. Add recent commits with format: `\`abc1234\` - "Commit message"`
2. Include meaningful accomplishments from recent work

## Best Practices

### 1. Proactive Task Management
- Update tasks **before** committing code
- Use Augment's task management tools consistently
- Keep task states current with actual progress

### 2. Meaningful Commit Messages
- Reference completed tasks in commit messages
- Include task IDs when relevant
- Explain the progress made

### 3. Regular Task List Maintenance
- Review task list weekly
- Update completion metrics regularly
- Document accomplishments as you complete them

### 4. Quality Checkpoints
- Run manual verification before important commits
- Address warnings even if they don't block commits
- Keep the task list as a living document

## Integration with Development Rules

### 1. Specification Adherence
- Verification ensures all work is tracked against specification
- Prevents "ghost" features that aren't documented

### 2. Task Management
- Enforces systematic task tracking
- Maintains visibility into project progress

### 3. Documentation Research
- Encourages documentation of research and decisions
- Links accomplishments to specific commits

### 4. Development Workflow
- Integrates quality gates into the commit process
- Maintains consistency across all development work

## Troubleshooting

### 1. Hook Not Running
- Verify hook is installed: `ls -la .git/hooks/pre-commit`
- Check hook permissions: `chmod +x .git/hooks/pre-commit`
- Reinstall hooks: `python scripts/install_git_hooks.py`

### 2. Python Script Errors
- Ensure Python 3 is available
- Check script permissions: `chmod +x scripts/verify_tasklist.py`
- Verify you're in the repository root

### 3. False Positives
- Review the specific error message
- Check if task list format matches expected patterns
- Ensure all required sections are present and properly formatted

## Customization

### 1. Adding New Checks
- Extend the `TaskListVerifier` class in `scripts/verify_tasklist.py`
- Add new verification methods following the existing pattern
- Update the `run_verification` method to include new checks

### 2. Modifying Requirements
- Update `REQUIRED_SECTIONS` list for different section requirements
- Modify regex patterns for different formatting needs
- Adjust warning vs. error classifications as needed

### 3. Integration with CI/CD
- Add verification to GitHub Actions workflows
- Include in automated testing pipelines
- Use as quality gate for pull requests

## Benefits

### 1. Consistency
- Ensures all team members maintain task lists properly
- Prevents inconsistent progress tracking

### 2. Visibility
- Maintains accurate project status at all times
- Enables reliable progress reporting

### 3. Quality
- Catches incomplete work documentation
- Enforces systematic development practices

### 4. Automation
- Reduces manual oversight burden
- Provides immediate feedback on compliance

This verification system ensures that our task management rules are consistently followed, maintaining the high-quality, systematic approach required for successful project delivery.
