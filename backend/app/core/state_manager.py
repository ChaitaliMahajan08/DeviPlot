import json
import threading
from pathlib import Path
from typing import Dict, List, Optional
from ..models.mission import (
    Mission,
    MissionStatus,
    AgentEvent,
    ToolExecutionRecord,
    TestResultRecord,
    ReviewFinding,
    RetryRecord,
    HumanApprovalRequest,
    FinalVerificationReport,
    VerificationOutcome
)
from ..config import settings

class MissionStateManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path(settings.DEFAULT_WORKSPACE) / ".devpilot" / "missions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._missions: Dict[str, Mission] = {}
        self._load_persisted_missions()

    def _get_file_path(self, task_id: str) -> Path:
        return self.storage_dir / f"{task_id}.json"

    def _load_persisted_missions(self):
        with self._lock:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        mission = Mission.model_validate(data)
                        self._missions[mission.task_id] = mission
                except Exception as e:
                    print(f"Warning: Failed to load mission from {file_path}: {e}")

    def save_mission(self, mission: Mission) -> Mission:
        with self._lock:
            import datetime
            mission.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self._missions[mission.task_id] = mission
            
            # Persist to disk
            file_path = self._get_file_path(mission.task_id)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(mission.model_dump_json(indent=2))
            return mission

    def get_mission(self, task_id: str) -> Optional[Mission]:
        with self._lock:
            if task_id in self._missions:
                return self._missions[task_id]
            file_path = self._get_file_path(task_id)
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        mission = Mission.model_validate_json(f.read())
                        self._missions[task_id] = mission
                        return mission
                except Exception:
                    return None
            return None

    def list_missions(self) -> List[Mission]:
        with self._lock:
            return sorted(
                list(self._missions.values()),
                key=lambda m: m.created_at,
                reverse=True
            )

    def add_agent_event(self, task_id: str, event: AgentEvent) -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            mission.agent_events.append(event)
            return self.save_mission(mission)

    def record_tool_call(self, task_id: str, record: ToolExecutionRecord) -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            mission.tool_calls.append(record)
            return self.save_mission(mission)

    def update_diff_and_files(self, task_id: str, diff: str, changed_files: List[str]) -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            mission.diff = diff
            for f in changed_files:
                if f not in mission.changed_files:
                    mission.changed_files.append(f)
            return self.save_mission(mission)

    def record_test_result(self, task_id: str, test_result: TestResultRecord) -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            mission.test_results.append(test_result)
            return self.save_mission(mission)

    def record_review_findings(self, task_id: str, findings: List[ReviewFinding], is_security: bool = False) -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            target_list = mission.security_findings if is_security else mission.review_findings
            for item in findings:
                # Avoid duplicate IDs
                if not any(existing.id == item.id for existing in target_list):
                    target_list.append(item)
            return self.save_mission(mission)

    def record_retry(self, task_id: str, retry: RetryRecord) -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            mission.retry_history.append(retry)
            mission.retry_count += 1
            mission.status = MissionStatus.RETRYING
            return self.save_mission(mission)

    def record_approval_request(self, task_id: str, request: HumanApprovalRequest) -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            mission.human_approvals.append(request)
            mission.status = MissionStatus.WAITING_FOR_APPROVAL
            return self.save_mission(mission)

    def submit_approval_decision(self, task_id: str, request_id: str, approved: bool, decided_by: str = "human_user") -> Mission:
        with self._lock:
            mission = self.get_mission(task_id)
            if not mission:
                raise KeyError(f"Mission {task_id} not found")
            import datetime
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            for req in mission.human_approvals:
                if req.id == request_id:
                    req.status = "APPROVED" if approved else "REJECTED"
                    req.decided_at = now_iso
                    req.decided_by = decided_by
                    break
                    
            if approved:
                mission.status = MissionStatus.IMPLEMENTING
            else:
                mission.status = MissionStatus.FAILED
                mission.unresolved_issues.append(f"Operation rejected by human operator ({decided_by}).")
                
            return self.save_mission(mission)

# Global singleton instance
mission_state_manager = MissionStateManager()
