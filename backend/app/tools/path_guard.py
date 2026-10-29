import os
from pathlib import Path

class SecurityViolation(Exception):
    pass

def validate_workspace_path(workspace_root: str, target_path: str) -> Path:
    """
    Validates and resolves target_path, guaranteeing that it resides
    strictly within workspace_root. Prevents directory traversal attacks (e.g. ../../etc/passwd).
    """
    try:
        resolved_root = Path(workspace_root).resolve()
        
        # If target_path is relative, resolve it relative to workspace_root
        candidate = Path(target_path)
        if not candidate.is_absolute():
            resolved_target = (resolved_root / candidate).resolve()
        else:
            resolved_target = candidate.resolve()
            
        # Verify containment
        # In Python 3.9+, is_relative_to is standard
        try:
            resolved_target.relative_to(resolved_root)
        except ValueError:
            raise SecurityViolation(
                f"Path traversal blocked: '{target_path}' resolves to '{resolved_target}' outside workspace '{resolved_root}'"
            )
            
        return resolved_target
    except Exception as e:
        if isinstance(e, SecurityViolation):
            raise
        raise SecurityViolation(f"Invalid path validation: {str(e)}")
