import re
from typing import List
from ..models.mission import ReviewFinding, ReviewSeverity
from ..config import settings

DANGEROUS_PATTERNS = [
    (r"(?i)\beval\s*\(", "Use of dynamic 'eval()' poses severe remote code execution vulnerability.", ReviewSeverity.CRITICAL, "Replace eval() with safe parsers like ast.literal_eval() or json.loads()."),
    (r"(?i)\bexec\s*\(", "Direct invocation of 'exec()' detected.", ReviewSeverity.CRITICAL, "Eliminate exec() in favor of structured static logic."),
    (r"(?i)pickle\.loads?\s*\(", "Insecure deserialization via pickle.", ReviewSeverity.HIGH, "Use JSON or Protocol Buffers for untrusted input."),
    (r"(?i)yaml\.load\s*\([^,)]+\)", "Unsafe PyYAML load() without Loader=SafeLoader.", ReviewSeverity.HIGH, "Use yaml.safe_load()."),
    (r"(?i)os\.system\s*\(.*[\+|%|format]", "Potential command injection via string formatting into os.system.", ReviewSeverity.HIGH, "Use subprocess.run with arguments passed as an explicit list."),
    (r"(?i)subprocess\.(?:Popen|call|run)\s*\(.*shell\s*=\s*True", "subprocess called with shell=True and dynamic input.", ReviewSeverity.MEDIUM, "Set shell=False and pass command as arguments list."),
    (r"(?i)select\s+.*\s+from\s+.*\s+where\s+.*[\+|%|format]", "Potential SQL injection pattern in query string concatenation.", ReviewSeverity.HIGH, "Use parameterized queries with prepared statements."),
    (r"(?i)open\s*\(.*(\.\./|\\\.\.\\)", "Hardcoded or unvalidated directory traversal sequence in file open.", ReviewSeverity.HIGH, "Validate paths using path containment checking (e.g. resolve and relative_to).")
]

def scan_text_for_security_issues(content: str, file_path: str = "workspace_file") -> List[ReviewFinding]:
    """Scans code text or git diff for credentials, secrets, and dangerous patterns."""
    findings: List[ReviewFinding] = []
    lines = content.split("\n")
    
    # 1. Secret Scanning
    for line_idx, line in enumerate(lines, 1):
        for pattern in settings.SAFETY.SECRET_REGEX_PATTERNS:
            match = re.search(pattern, line)
            if match:
                findings.append(ReviewFinding(
                    id=f"sec_secret_{file_path}_{line_idx}",
                    severity=ReviewSeverity.CRITICAL,
                    category="security",
                    file_path=file_path,
                    line_number=line_idx,
                    description="Exposed credential or secret token detected in source or diff.",
                    fix_suggestion="Extract credential to an external environment variable or secure secrets manager. Never commit secrets.",
                    resolved=False
                ))
                break

    # 2. Dangerous Code Patterns
    for line_idx, line in enumerate(lines, 1):
        for pattern, desc, severity, remediation in DANGEROUS_PATTERNS:
            if re.search(pattern, line):
                findings.append(ReviewFinding(
                    id=f"sec_pattern_{file_path}_{line_idx}",
                    severity=severity,
                    category="security",
                    file_path=file_path,
                    line_number=line_idx,
                    description=desc,
                    fix_suggestion=remediation,
                    resolved=False
                ))

    return findings
