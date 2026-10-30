import os
from pathlib import Path
from typing import List, Set

BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Use /tmp for runtime data to avoid fuse/IO issues on some mounted volumes
DATA_DIR = Path(os.getenv("DEVPILOT_DATA_DIR", "/tmp/devpilot_data"))
MISSIONS_DIR = DATA_DIR / "missions"
FIXTURES_DIR = BASE_DIR / "backend" / "fixtures"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
MISSIONS_DIR.mkdir(parents=True, exist_ok=True)

class SafetyPolicy:
    DEFAULT_COMMAND_TIMEOUT_SECONDS: int = 45
    MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024  # 2MB
    MAX_OUTPUT_CHARS: int = 10000

    # Patterns strictly forbidden in terminal execution
    BLOCKED_COMMAND_PATTERNS: List[str] = [
        "rm -rf /",
        "rm -rf /*",
        "rmdir /s /q c:\\",
        "format ",
        "mkfs",
        "dd if=",
        "shutdown",
        "reboot",
        ":(){ :|:& };:",
        "git push --force",
        "git reset --hard HEAD~",
        "> /dev/sda",
        "chmod -R 777 /",
    ]

    # Sensitive operations requiring human approval before execution
    APPROVAL_REQUIRED_OPERATIONS: Set[str] = {
        "git_commit_and_push",
        "destructive_file_delete",
        "install_global_package",
        "external_network_call",
    }

    # Secret patterns for scanning diffs and logs
    SECRET_REGEX_PATTERNS = [
        r"(?i)api[-_]?key\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{16,})['\"]",
        r"(?i)secret[-_]?token\s*[:=]\s*['\"]([a-zA-Z0-9_\-]{16,})['\"]",
        r"(?i)password\s*[:=]\s*['\"][^'\"]{6,}['\"]",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        r"ghp_[a-zA-Z0-9]{36}",  # GitHub personal token
        r"sk-[a-zA-Z0-9]{32,}",   # OpenAI API key pattern
        r"AIza[0-9A-Za-z-_]{35}", # Google API key pattern
        r"AKIA[0-9A-Z]{16}",      # AWS Access Key
    ]

class Settings:
    HOST: str = os.getenv("DEVPILOT_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("DEVPILOT_PORT", 5000))
    DEBUG: bool = os.getenv("DEVPILOT_DEBUG", "True").lower() in ("true", "1")
    SECRET_KEY: str = os.getenv("DEVPILOT_SECRET_KEY", "devpilot-guild-secret-pecathon-2026")
    DEFAULT_MAX_RETRIES: int = int(os.getenv("DEVPILOT_MAX_RETRIES", 2))
    DEFAULT_WORKSPACE: str = str(BASE_DIR)
    SAFETY: SafetyPolicy = SafetyPolicy()

settings = Settings()
