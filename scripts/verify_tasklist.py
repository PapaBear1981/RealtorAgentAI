#!/usr/bin/env python3
"""
Task List Verification System
Multi-Agent Real-Estate Contract Platform

This script verifies that the MASTER_TASK_LIST.md has been properly updated
before allowing git commits. It ensures compliance with our task management rules.

Usage:
    python scripts/verify_tasklist.py
    
Exit codes:
    0: Task list is properly updated
    1: Task list verification failed
    2: Critical errors (missing files, etc.)
"""

import os
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuration
TASK_LIST_FILE = "MASTER_TASK_LIST.md"
REQUIRED_SECTIONS = [
    "Task Management Rules Reference",
    "Current Task Status Overview", 
    "Completion Metrics",
    "Next Immediate Steps",
    "Recent Accomplishments"
]

class TaskListVerifier:
    def __init__(self):
        self.repo_root = self._find_repo_root()
        self.task_list_path = self.repo_root / TASK_LIST_FILE
        self.errors = []
        self.warnings = []
        
    def _find_repo_root(self) -> Path:
        """Find the repository root directory."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        raise RuntimeError("Not in a git repository")
    
    def _get_git_status(self) -> Dict[str, List[str]]:
        """Get git status information."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            
            status = {"modified": [], "added": [], "deleted": []}
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                status_code = line[:2]
                filename = line[3:]
                
                if 'M' in status_code:
                    status["modified"].append(filename)
                elif 'A' in status_code:
                    status["added"].append(filename)
                elif 'D' in status_code:
                    status["deleted"].append(filename)
                    
            return status
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Failed to get git status: {e}")
            return {"modified": [], "added": [], "deleted": []}
    
    def _get_staged_files(self) -> List[str]:
        """Get list of staged files."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []
    
    def verify_file_exists(self) -> bool:
        """Verify that the task list file exists."""
        if not self.task_list_path.exists():
            self.errors.append(f"Task list file not found: {TASK_LIST_FILE}")
            return False
        return True
    
    def verify_file_structure(self) -> bool:
        """Verify that the task list has required sections."""
        try:
            content = self.task_list_path.read_text(encoding='utf-8')
        except Exception as e:
            self.errors.append(f"Failed to read task list: {e}")
            return False
        
        missing_sections = []
        for section in REQUIRED_SECTIONS:
            if section not in content:
                missing_sections.append(section)
        
        if missing_sections:
            self.errors.append(f"Missing required sections: {', '.join(missing_sections)}")
            return False
            
        return True
    
    def verify_last_updated(self) -> bool:
        """Verify that the 'Last Updated' field is current."""
        try:
            content = self.task_list_path.read_text(encoding='utf-8')
            
            # Look for Last Updated pattern
            pattern = r'\*\*Last Updated\*\*:\s*(\d{4}-\d{2}-\d{2})'
            match = re.search(pattern, content)
            
            if not match:
                self.warnings.append("No 'Last Updated' field found in task list")
                return True  # Warning, not error
            
            last_updated = match.group(1)
            today = datetime.now().strftime('%Y-%m-%d')
            
            if last_updated != today:
                self.warnings.append(f"Task list 'Last Updated' is {last_updated}, should be {today}")
                
        except Exception as e:
            self.warnings.append(f"Could not verify last updated date: {e}")
            
        return True
    
    def verify_completion_metrics(self) -> bool:
        """Verify that completion metrics are present and reasonable."""
        try:
            content = self.task_list_path.read_text(encoding='utf-8')
            
            # Look for completion metrics
            patterns = {
                'total': r'\*\*Total Tasks\*\*:\s*(\d+)',
                'completed': r'\*\*Completed\*\*:\s*(\d+)',
                'in_progress': r'\*\*In Progress\*\*:\s*(\d+)',
                'not_started': r'\*\*Not Started\*\*:\s*(\d+)'
            }
            
            metrics = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    metrics[key] = int(match.group(1))
                else:
                    self.warnings.append(f"Missing completion metric: {key}")
                    return True
            
            # Verify math adds up
            if 'total' in metrics:
                calculated_total = metrics.get('completed', 0) + metrics.get('in_progress', 0) + metrics.get('not_started', 0)
                if calculated_total != metrics['total']:
                    self.errors.append(f"Completion metrics don't add up: {calculated_total} != {metrics['total']}")
                    return False
                    
        except Exception as e:
            self.warnings.append(f"Could not verify completion metrics: {e}")
            
        return True
    
    def verify_task_states(self) -> bool:
        """Verify that task states are properly formatted."""
        try:
            content = self.task_list_path.read_text(encoding='utf-8')
            
            # Count different task states
            task_patterns = {
                'not_started': r'- \[ \]',
                'in_progress': r'- \[/\]', 
                'completed': r'- \[x\]',
                'cancelled': r'- \[-\]'
            }
            
            task_counts = {}
            for state, pattern in task_patterns.items():
                matches = re.findall(pattern, content)
                task_counts[state] = len(matches)
            
            total_tasks = sum(task_counts.values())
            if total_tasks == 0:
                self.warnings.append("No task checkboxes found in task list")
                
        except Exception as e:
            self.warnings.append(f"Could not verify task states: {e}")
            
        return True
    
    def verify_recent_accomplishments(self) -> bool:
        """Verify that recent accomplishments section is updated."""
        try:
            content = self.task_list_path.read_text(encoding='utf-8')
            
            # Look for recent accomplishments section
            if "Recent Accomplishments" not in content:
                self.warnings.append("No 'Recent Accomplishments' section found")
                return True
            
            # Check if there are recent commit references
            commit_pattern = r'`[a-f0-9]{7}`'
            commits = re.findall(commit_pattern, content)
            
            if not commits:
                self.warnings.append("No recent commit references found in accomplishments")
                
        except Exception as e:
            self.warnings.append(f"Could not verify recent accomplishments: {e}")
            
        return True
    
    def verify_staged_changes(self) -> bool:
        """Verify that if code changes are staged, task list is also staged."""
        staged_files = self._get_staged_files()
        
        if not staged_files:
            return True  # No staged changes
        
        # Check if there are significant code changes staged
        code_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.vue', '.go', '.rs', '.java', '.cpp', '.c'}
        config_files = {'docker-compose.yml', 'Dockerfile', 'package.json', 'requirements.txt', 'pyproject.toml'}
        
        has_code_changes = any(
            Path(f).suffix in code_extensions or Path(f).name in config_files
            for f in staged_files
        )
        
        task_list_staged = TASK_LIST_FILE in staged_files
        
        if has_code_changes and not task_list_staged:
            self.errors.append(
                f"Code changes are staged but {TASK_LIST_FILE} is not staged. "
                "Please update the task list to reflect your progress."
            )
            return False
            
        return True
    
    def run_verification(self) -> bool:
        """Run all verification checks."""
        print("Verifying task list compliance...")
        
        checks = [
            ("File exists", self.verify_file_exists),
            ("File structure", self.verify_file_structure),
            ("Last updated", self.verify_last_updated),
            ("Completion metrics", self.verify_completion_metrics),
            ("Task states", self.verify_task_states),
            ("Recent accomplishments", self.verify_recent_accomplishments),
            ("Staged changes", self.verify_staged_changes),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                result = check_func()
                status = "[PASS]" if result else "[FAIL]"
                print(f"  {status} {check_name}")
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"  [FAIL] {check_name} (error: {e})")
                self.errors.append(f"{check_name} check failed: {e}")
                all_passed = False

        # Print warnings
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        # Print errors
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        if all_passed and not self.errors:
            print("\nTask list verification passed!")
            return True
        else:
            print(f"\nTask list verification failed with {len(self.errors)} errors")
            return False

def main():
    """Main entry point."""
    try:
        verifier = TaskListVerifier()
        success = verifier.run_verification()
        
        if success:
            sys.exit(0)
        else:
            print("\nTo fix these issues:")
            print("  1. Update your task progress using Augment's task management tools")
            print("  2. Update completion metrics in MASTER_TASK_LIST.md")
            print("  3. Add recent accomplishments with commit references")
            print("  4. Stage the updated task list file")
            sys.exit(1)

    except Exception as e:
        print(f"Critical error during verification: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
