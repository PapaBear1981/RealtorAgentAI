# Task List Verification System - Quick Guide

## 🎯 Purpose
Automatically ensures that `MASTER_TASK_LIST.md` is properly updated before every git commit, maintaining accurate progress tracking and project visibility.

## 🚀 Quick Start

### 1. Installation (Already Done)
```bash
python scripts/install_git_hooks.py
```

### 2. Normal Workflow
```bash
# 1. Make your code changes
# 2. Update task progress using Augment tools
update_tasks([{"task_id": "task-uuid", "state": "COMPLETE"}])

# 3. Update MASTER_TASK_LIST.md if needed
# 4. Stage and commit (verification runs automatically)
git add .
git commit -m "Your commit message"
```

## ✅ What Gets Verified

### Automatic Checks
- **File exists**: MASTER_TASK_LIST.md is present
- **Structure**: Required sections are present
- **Metrics**: Task counts add up correctly
- **States**: Task checkboxes are properly formatted
- **Staging**: Task list is staged when code changes are staged
- **Accomplishments**: Recent work is documented

### Example Output
```
Verifying task list compliance...
  [PASS] File exists
  [PASS] File structure
  [PASS] Last updated
  [PASS] Completion metrics
  [PASS] Task states
  [PASS] Recent accomplishments
  [PASS] Staged changes

Task list verification passed!
```

## 🔧 Manual Testing
```bash
# Test verification without committing
python scripts/verify_tasklist.py
```

## 🚨 When Verification Fails

### Common Error: "Code changes staged but task list not staged"
```bash
# Fix by staging the updated task list
git add MASTER_TASK_LIST.md
git commit -m "Your message"
```

### Common Error: "Completion metrics don't add up"
```bash
# Fix by updating the metrics in MASTER_TASK_LIST.md
# Ensure: Total = Completed + In Progress + Not Started + Cancelled
```

## 🆘 Emergency Bypass (Not Recommended)
```bash
# Only use in true emergencies
git commit --no-verify -m "Emergency commit"
```

## 📋 Required Task List Sections
- Task Management Rules Reference
- Current Task Status Overview
- Completion Metrics
- Next Immediate Steps
- Recent Accomplishments

## 🎯 Benefits
- **Consistency**: Ensures all progress is tracked
- **Visibility**: Maintains accurate project status
- **Quality**: Prevents incomplete documentation
- **Automation**: No manual oversight needed

## 📚 Full Documentation
See `development-rules/05-task-list-verification-rules.md` for complete details.

---

**The verification system is now active and will run on every commit!** 🛡️
