import uuid
import json
from typing import Dict, Any, List, Tuple
from .base import BaseAgent
from ..models.mission import Mission, AcceptanceCriterion, CriterionStatus, PlannedTask, MissionStatus
from ..core.state_manager import mission_state_manager

class ShogunPlanner(BaseAgent):
    def __init__(self):
        super().__init__(
            name="shogun",
            role="Planner & Guild Master",
            title="Strategic Commander of Reconnaissance and Planning"
        )

    def plan_mission(self, mission: Mission) -> Tuple[List[AcceptanceCriterion], List[PlannedTask], Dict[str, Any]]:
        self.dispatch_event(
            task_id=mission.task_id,
            recipient="orchestrator",
            event_type="analysis",
            content=f"Shogun initiated reconnaissance for mission: '{mission.user_request}'",
            next_action="inspect_workspace"
        )

        # 1. Ambiguity detection
        req_clean = mission.user_request.strip()
        if len(req_clean) < 4 or req_clean.lower() in ("test", "help", "do something", "fix it"):
            self.dispatch_event(
                task_id=mission.task_id,
                recipient="user",
                event_type="clarification_request",
                content="The requested specification is ambiguous or insufficient to formulate verifiable acceptance criteria. Please specify the target module, feature requirement, or defect description.",
                next_action="await_user_clarification"
            )
            mission.status = MissionStatus.NEEDS_CLARIFICATION
            mission.unresolved_issues.append("Task request lacked actionable specifications.")
            mission_state_manager.save_mission(mission)
            return [], [], {"error": "AMBIGUOUS_REQUEST"}

        # 2. Repository Reconnaissance
        list_record = self.call_tool(
            task_id=mission.task_id,
            workspace=mission.workspace_path,
            tool_name="list_files",
            arguments={"subpath": ""}
        )
        
        recon_files = []
        try:
            recon_files = json.loads(list_record.output)
        except Exception:
            pass

        # Identify tests, dependencies, and entrypoints
        test_files = [f["path"] for f in recon_files if "test" in f["path"].lower()]
        py_files = [f["path"] for f in recon_files if f["path"].endswith(".py") and not f["is_dir"]]
        js_files = [f["path"] for f in recon_files if f["path"].endswith((".js", ".ts", ".jsx", ".tsx")) and not f["is_dir"]]
        
        recon_summary = {
            "total_files": len(recon_files),
            "test_files": test_files,
            "py_files": py_files,
            "js_files": js_files,
            "has_existing_tests": len(test_files) > 0
        }

        self.dispatch_event(
            task_id=mission.task_id,
            recipient="orchestrator",
            event_type="reconnaissance_report",
            content=f"Reconnaissance complete: Identified {len(recon_files)} repository items, {len(test_files)} test suite files, {len(py_files)} Python source modules.",
            evidence=json.dumps(recon_summary, indent=2),
            next_action="formulate_acceptance_criteria"
        )

        # 3. Acceptance Criteria Generation
        criteria: List[AcceptanceCriterion] = []
        
        # Primary functional criterion
        criteria.append(AcceptanceCriterion(
            id=f"AC-1",
            description=f"Satisfy user requirement: '{mission.user_request[:120]}'",
            status=CriterionStatus.PENDING
        ))
        
        # Test verification criterion
        if test_files:
            criteria.append(AcceptanceCriterion(
                id=f"AC-2",
                description=f"Execute and pass automated test suite across verified test files: {', '.join(test_files[:3])}",
                status=CriterionStatus.PENDING
            ))
        else:
            criteria.append(AcceptanceCriterion(
                id=f"AC-2",
                description="Construct targeted automated tests or verification checks validating the changes.",
                status=CriterionStatus.PENDING
            ))

        # Security and Code Integrity criterion
        criteria.append(AcceptanceCriterion(
            id=f"AC-3",
            description="Ensure no exposed credentials, unsafe dynamic execution, or regressions in existing code.",
            status=CriterionStatus.PENDING
        ))

        # 4. Task Decomposition
        tasks: List[PlannedTask] = [
            PlannedTask(
                id="TASK-1",
                title="Deep File Inspection & Context Reading",
                description="Samurai locates and reads target implementation files and surrounding dependencies.",
                assigned_agent="samurai",
                status="PENDING",
                dependencies=[]
            ),
            PlannedTask(
                id="TASK-2",
                title="Context-Aware Implementation",
                description="Samurai applies bounded, verified edits to code files according to conventions.",
                assigned_agent="samurai",
                status="PENDING",
                dependencies=["TASK-1"]
            ),
            PlannedTask(
                id="TASK-3",
                title="Automated Test Execution & Failure Analysis",
                description="Sentinel discovers test runner, runs checks, captures exit codes, and diagnoses results.",
                assigned_agent="sentinel",
                status="PENDING",
                dependencies=["TASK-2"]
            ),
            PlannedTask(
                id="TASK-4",
                title="Security Scan & Council Review",
                description="Shadow Council inspects diff for secret leakage, dangerous syntax, and code quality.",
                assigned_agent="shadow_council",
                status="PENDING",
                dependencies=["TASK-3"]
            ),
            PlannedTask(
                id="TASK-5",
                title="Independent Verification & Mission Report",
                description="Orchestrator cross-examines criteria, test evidence, and review verdict for final report.",
                assigned_agent="shogun",
                status="PENDING",
                dependencies=["TASK-4"]
            )
        ]

        # Update mission
        mission.acceptance_criteria = criteria
        mission.plan = tasks
        mission_state_manager.save_mission(mission)

        self.dispatch_event(
            task_id=mission.task_id,
            recipient="samurai",
            event_type="handoff",
            content=f"Plan formulated with {len(criteria)} acceptance criteria and {len(tasks)} decomposed tasks. Handing off mission execution to Samurai.",
            evidence=f"Acceptance Criteria:\n" + "\n".join([f"- [{c.id}] {c.description}" for c in criteria]),
            next_action="start_development"
        )

        return criteria, tasks, recon_summary
