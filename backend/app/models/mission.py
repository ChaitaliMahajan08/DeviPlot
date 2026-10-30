from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import datetime

class MissionStatus(str, Enum):
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    RECONNAISSANCE = "RECONNAISSANCE"
    IMPLEMENTING = "IMPLEMENTING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    RETRYING = "RETRYING"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class CriterionStatus(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    UNCHECKED = "UNCHECKED"

class AcceptanceCriterion(BaseModel):
    id: str
    description: str
    status: CriterionStatus = CriterionStatus.PENDING
    evidence: Optional[str] = None

class PlannedTask(BaseModel):
    id: str
    title: str
    description: str
    assigned_agent: str  # "shogun", "samurai", "sentinel", "shadow_council"
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED, BLOCKED
    dependencies: List[str] = Field(default_factory=list)

class AgentEvent(BaseModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    sender: str  # e.g., "shogun", "samurai", "sentinel", "shadow_council", "orchestrator", "user"
    recipient: str  # e.g., "orchestrator", "samurai", "sentinel", "all"
    event_type: str  # "analysis", "handoff", "code_edit", "test_report", "review_finding", "approval_request", "plan_revision"
    content: str
    evidence: Optional[str] = None
    next_action: Optional[str] = None

class ToolExecutionRecord(BaseModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    tool_name: str
    input_summary: str
    target_path: Optional[str] = None
    command: Optional[str] = None
    status: str  # "SUCCESS", "FAILED", "BLOCKED", "APPROVAL_REQUIRED"
    exit_code: Optional[int] = None
    output: str = ""
    error_details: Optional[str] = None
    duration_ms: float = 0.0
    blocked_reason: Optional[str] = None

class TestResultRecord(BaseModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    command: str
    exit_code: int
    passed_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    failure_details: List[str] = Field(default_factory=list)

class ReviewSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class ReviewFinding(BaseModel):
    id: str
    severity: ReviewSeverity
    category: str  # "correctness", "security", "style", "regression"
    file_path: str
    line_number: Optional[int] = None
    description: str
    fix_suggestion: Optional[str] = None
    resolved: bool = False
    resolution_evidence: Optional[str] = None

class RetryRecord(BaseModel):
    attempt: int
    stage: str
    reason: str
    evidence: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

class HumanApprovalRequest(BaseModel):
    id: str
    action_type: str  # e.g., "merge_changes", "execute_sensitive_command", "external_api"
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"  # "PENDING", "APPROVED", "REJECTED"
    requested_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None

class VerificationOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    FAILED = "FAILED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"

class FinalVerificationReport(BaseModel):
    outcome: VerificationOutcome
    summary: str
    verified_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    criteria_summary: Dict[str, Any] = Field(default_factory=dict)
    tests_summary: Dict[str, Any] = Field(default_factory=dict)
    reviews_summary: Dict[str, Any] = Field(default_factory=dict)
    unresolved_risks: List[str] = Field(default_factory=list)

class Mission(BaseModel):
    task_id: str
    user_request: str
    workspace_path: str
    status: MissionStatus = MissionStatus.QUEUED
    current_phase: str = "INITIALIZATION"
    acceptance_criteria: List[AcceptanceCriterion] = Field(default_factory=list)
    plan: List[PlannedTask] = Field(default_factory=list)
    plan_version: int = 1
    plan_revision_reason: Optional[str] = None
    agent_events: List[AgentEvent] = Field(default_factory=list)
    tool_calls: List[ToolExecutionRecord] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    diff: str = ""
    test_results: List[TestResultRecord] = Field(default_factory=list)
    review_findings: List[ReviewFinding] = Field(default_factory=list)
    security_findings: List[ReviewFinding] = Field(default_factory=list)
    retry_history: List[RetryRecord] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    human_approvals: List[HumanApprovalRequest] = Field(default_factory=list)
    unresolved_issues: List[str] = Field(default_factory=list)
    final_verification: Optional[FinalVerificationReport] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
