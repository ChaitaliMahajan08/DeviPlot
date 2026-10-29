import subprocess
from typing import Dict, Any, List
from pathlib import Path
from .terminal import execute_workspace_command

def get_git_diff(workspace: str, staged_only: bool = False) -> str:
    """Retrieves actual git diff from workspace repository."""
    cmd = "git diff --staged" if staged_only else "git diff HEAD"
    res = execute_workspace_command(workspace, cmd, timeout=15)
    if res["exit_code"] != 0:
        # Fallback to unstaged git diff if HEAD ref does not exist yet (initial commit)
        res_fallback = execute_workspace_command(workspace, "git diff", timeout=15)
        return res_fallback["stdout"]
    return res["stdout"]

def get_git_status(workspace: str) -> Dict[str, Any]:
    """Retrieves structured git status from workspace repository."""
    res = execute_workspace_command(workspace, "git status --porcelain", timeout=15)
    lines = res["stdout"].strip().split("\n") if res["stdout"].strip() else []
    
    modified = []
    untracked = []
    staged = []
    
    for line in lines:
        if len(line) < 3:
            continue
        index_code = line[0]
        worktree_code = line[1]
        path = line[3:].strip()
        
        if index_code in ("M", "A", "D"):
            staged.append(path)
        if worktree_code == "M":
            modified.append(path)
        elif index_code == "?" and worktree_code == "?":
            untracked.append(path)
            
    return {
        "is_clean": len(lines) == 0,
        "modified": modified,
        "untracked": untracked,
        "staged": staged,
        "raw": res["stdout"]
    }
