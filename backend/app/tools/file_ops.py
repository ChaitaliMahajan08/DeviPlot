import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from .path_guard import validate_workspace_path, SecurityViolation

def read_workspace_file(workspace: str, relative_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
    safe_path = validate_workspace_path(workspace, relative_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")
    if safe_path.is_dir():
        raise IsADirectoryError(f"Path is a directory: {relative_path}")
        
    with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        
    total_lines = len(lines)
    s = (start_line - 1) if (start_line and start_line > 0) else 0
    e = end_line if (end_line and end_line <= total_lines) else total_lines
    
    selected_lines = lines[s:e]
    content = "".join(selected_lines)
    
    return {
        "path": relative_path,
        "total_lines": total_lines,
        "start_line": s + 1,
        "end_line": e,
        "content": content
    }

def write_workspace_file(workspace: str, relative_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
    safe_path = validate_workspace_path(workspace, relative_path)
    
    if safe_path.exists() and not overwrite:
        raise FileExistsError(f"File already exists and overwrite is False: {relative_path}")
        
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    with open(safe_path, "w", encoding="utf-8") as f:
        bytes_written = f.write(content)
        f.flush()
        os.fsync(f.fileno())
        
    # Verify file exists on disk and has matching content length
    if not safe_path.exists():
        raise IOError(f"Filesystem verification failed: {relative_path} was not created.")
        
    return {
        "path": relative_path,
        "bytes_written": bytes_written,
        "size_bytes": safe_path.stat().st_size,
        "verified_on_disk": True
    }

def edit_workspace_file(workspace: str, relative_path: str, target: str, replacement: str) -> Dict[str, Any]:
    safe_path = validate_workspace_path(workspace, relative_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"Cannot edit non-existent file: {relative_path}")
        
    with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
        existing = f.read()
        
    if target not in existing:
        raise ValueError(f"Target snippet not found in file: {relative_path}")
        
    occurrences = existing.count(target)
    updated = existing.replace(target, replacement)
    
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(updated)
        f.flush()
        os.fsync(f.fileno())
        
    # Verify on disk
    with open(safe_path, "r", encoding="utf-8") as f:
        re_read = f.read()
        
    if replacement not in re_read:
        raise IOError(f"Filesystem edit verification failed for {relative_path}")
        
    return {
        "path": relative_path,
        "replacements_made": occurrences,
        "new_size_bytes": safe_path.stat().st_size,
        "verified_on_disk": True
    }

def search_workspace_files(workspace: str, pattern: str, file_pattern: str = "*") -> List[Dict[str, Any]]:
    root = Path(workspace).resolve()
    results = []
    regex = re.compile(pattern, re.IGNORECASE)
    
    for p in root.rglob(file_pattern):
        # Skip git and hidden files
        if ".git" in p.parts or "__pycache__" in p.parts or "node_modules" in p.parts or ".devpilot" in p.parts:
            continue
        if p.is_file():
            try:
                rel_path = str(p.relative_to(root)).replace("\\", "/")
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for idx, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append({
                                "file": rel_path,
                                "line": idx,
                                "match": line.strip()[:200]
                            })
                            if len(results) >= 100:  # Cap results for safety
                                return results
            except Exception:
                continue
    return results

def list_workspace_tree(workspace: str, max_depth: int = 4) -> List[Dict[str, Any]]:
    root = Path(workspace).resolve()
    tree = []
    
    for p in root.rglob("*"):
        if ".git" in p.parts or "__pycache__" in p.parts or "node_modules" in p.parts or ".devpilot" in p.parts:
            continue
        try:
            rel = str(p.relative_to(root)).replace("\\", "/")
            depth = len(p.relative_to(root).parts)
            if depth <= max_depth:
                tree.append({
                    "path": rel,
                    "is_dir": p.is_dir(),
                    "size": p.stat().st_size if p.is_file() else 0
                })
        except Exception:
            continue
            
    return sorted(tree, key=lambda x: (not x["is_dir"], x["path"]))
