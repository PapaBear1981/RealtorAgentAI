#!/usr/bin/env python3
"""
Git Hooks Installation Script
Multi-Agent Real-Estate Contract Platform

This script installs Git hooks to ensure task list compliance and code quality.
"""

import os
import sys
import stat
from pathlib import Path

def find_repo_root():
    """Find the repository root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Not in a git repository")

def create_pre_commit_hook():
    """Create the pre-commit hook."""
    hook_content = '''#!/bin/bash
# Pre-commit hook for Multi-Agent Real-Estate Contract Platform
# Ensures task list compliance before commits

echo "Running pre-commit checks..."

# Run task list verification
python3 scripts/verify_tasklist.py
TASKLIST_EXIT_CODE=$?

if [ $TASKLIST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Pre-commit hook failed: Task list verification failed"
    echo ""
    echo "Please ensure:"
    echo "  1. MASTER_TASK_LIST.md is updated with your progress"
    echo "  2. Task states are properly marked ([ ], [/], [x], [-])"
    echo "  3. Completion metrics are accurate"
    echo "  4. Recent accomplishments are documented"
    echo "  5. Task list file is staged for commit"
    echo ""
    echo "Use 'git commit --no-verify' to bypass this check (not recommended)"
    exit 1
fi

echo "Pre-commit checks passed!"
exit 0
'''
    return hook_content

def install_hooks():
    """Install Git hooks."""
    try:
        repo_root = find_repo_root()
        hooks_dir = repo_root / ".git" / "hooks"
        
        # Ensure hooks directory exists
        hooks_dir.mkdir(exist_ok=True)
        
        # Install pre-commit hook
        pre_commit_path = hooks_dir / "pre-commit"
        
        print(f"📝 Installing pre-commit hook to {pre_commit_path}")
        
        with open(pre_commit_path, 'w', encoding='utf-8') as f:
            f.write(create_pre_commit_hook())
        
        # Make hook executable
        st = os.stat(pre_commit_path)
        os.chmod(pre_commit_path, st.st_mode | stat.S_IEXEC)
        
        print("✅ Git hooks installed successfully!")
        print("")
        print("The pre-commit hook will now:")
        print("  • Verify task list is properly updated")
        print("  • Check completion metrics are accurate")
        print("  • Ensure recent accomplishments are documented")
        print("  • Validate task states are properly formatted")
        print("")
        print("To bypass the hook (not recommended): git commit --no-verify")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to install Git hooks: {e}")
        return False

def main():
    """Main entry point."""
    print("🔧 Installing Git hooks for task list verification...")
    
    if install_hooks():
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
