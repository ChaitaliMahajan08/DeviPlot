import subprocess
import time
import re
from typing import Dict, Any, Tuple
from ..config import settings
from .path_guard import SecurityViolation

def mask_secrets(text: str) -> str:
    """Masks tokens, keys, and passwords from logs and tool output."""
    masked = text
    for pattern in settings.SAFETY.SECRET_REGEX_PATTERNS:
        try:
            masked = re.sub(pattern, "[MASKED_SECRET]", masked)
        except Exception:
            continue
    return masked

def execute_workspace_command(workspace: str, command: str, timeout: int = settings.SAFETY.DEFAULT_COMMAND_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """
    Executes a shell command strictly inside the workspace working directory,
    enforcing command blacklisting and process timeouts.
    """
    # 1. Check for blocked malicious or destructive commands
    lower_cmd = command.lower().strip()
    for blocked in settings.SAFETY.BLOCKED_COMMAND_PATTERNS:
        if blocked.lower() in lower_cmd:
            raise SecurityViolation(f"Command execution blocked by DevPilot Safety Policy: contains dangerous pattern '{blocked}'")
            
    start_time = time.time()
    
    try:
        # Execute subprocess
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        stdout, stderr = proc.communicate(timeout=timeout)
        duration_ms = (time.time() - start_time) * 1000
        
        # Truncate output if exceeding limits to prevent OOM
        max_chars = settings.SAFETY.MAX_OUTPUT_CHARS
        if len(stdout) > max_chars:
            stdout = stdout[:max_chars] + f"\n... [Output truncated at {max_chars} characters]"
        if len(stderr) > max_chars:
            stderr = stderr[:max_chars] + f"\n... [Stderr truncated at {max_chars} characters]"
            
        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": mask_secrets(stdout),
            "stderr": mask_secrets(stderr),
            "duration_ms": round(duration_ms, 2),
            "timed_out": False
        }
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        duration_ms = (time.time() - start_time) * 1000
        return {
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds.",
            "duration_ms": round(duration_ms, 2),
            "timed_out": True
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Process execution error: {str(e)}",
            "duration_ms": round(duration_ms, 2),
            "timed_out": False
        }
