import re
import uuid
import json
from typing import Dict, Any, List, Tuple
from .base import BaseAgent
from ..models.mission import (
    Mission,
    TestResultRecord,
    CriterionStatus,
    AcceptanceCriterion
)
from ..core.state_manager import mission_state_manager

class SentinelTester(BaseAgent):
    def __init__(self):
        super().__init__(
            name="sentinel",
            role="QA & Independent Verifier",
            title="Rigorous Guardian of Evidence-Backed Testing"
        )

    def discover_and_run_tests(self, mission: Mission) -> Tuple[bool, TestResultRecord]:
        task_id = mission.task_id
        workspace = mission.workspace_path

        self.dispatch_event(
            task_id=task_id,
            recipient="orchestrator",
            event_type="test_discovery",
            content="Sentinel discovering available automated test harnesses in repository..."
        )

        # 1. Discover test files
        list_rec = self.call_tool(task_id=task_id, workspace=workspace, tool_name="list_files", arguments={})
        try:
            tree = json.loads(list_rec.output)
        except Exception:
            tree = []

        test_files = [item["path"] for item in tree if "test" in item["path"].lower() and item["path"].endswith(".py")]
        js_test_files = [item["path"] for item in tree if "test" in item["path"].lower() and item["path"].endswith((".js", ".ts"))]
        package_json = any(item["path"] == "package.json" for item in tree)

        test_command = None
        if test_files:
            # Prefer python -m unittest discover or specific test file
            if len(test_files) == 1:
                test_command = f"python -m unittest {test_files[0]}"
            else:
                test_command = "python -m unittest discover -s . -p \"*test*.py\""
        elif js_test_files or package_json:
            test_command = "npm test"
        else:
            # Repository has no automated tests! Report this fact honestly per PS-001
            self.dispatch_event(
                task_id=task_id,
                recipient="orchestrator",
                event_type="test_warning",
                content="No existing automated test suite detected in repository. Sentinel will verify syntax via Python compile check.",
                evidence="No test_*.py or package.json test scripts discovered."
            )
            # Run python syntax check across python files
            test_command = "python -m compileall ."

        self.dispatch_event(
            task_id=task_id,
            recipient="orchestrator",
            event_type="test_execution_start",
            content=f"Sentinel executing real test command: `{test_command}`"
        )

        # Execute test command
        cmd_rec = self.call_tool(
            task_id=task_id,
            workspace=workspace,
            tool_name="run_command",
            arguments={"command": test_command, "timeout": 40}
        )

        # Parse test metrics from stdout/stderr
        raw_output = (cmd_rec.output or "") + "\n" + (cmd_rec.error_details or "")
        exit_code = cmd_rec.exit_code if cmd_rec.exit_code is not None else -1
        
        passed_count = 0
        failed_count = 0
        total_count = 0
        failure_details: List[str] = []

        # Standard unittest output parsing: "Ran X tests in Ys\nFAILED (failures=A, errors=B)" or "OK"
        ran_match = re.search(r"Ran\s+(\d+)\s+tests?", raw_output)
        if ran_match:
            total_count = int(ran_match.group(1))

        if "OK" in raw_output and exit_code == 0:
            passed_count = total_count
            is_success = True
        else:
            is_success = exit_code == 0
            if not is_success:
                # Extract assertion failures or errors
                for line in raw_output.split("\n"):
                    if "AssertionError" in line or "FAIL:" in line or "ERROR:" in line or "Error:" in line:
                        failure_details.append(line.strip()[:180])
                failed_count = max(1, total_count - passed_count)
            else:
                passed_count = total_count

        test_record = TestResultRecord(
            id=f"test_{uuid.uuid4().hex[:8]}",
            command=test_command,
            exit_code=exit_code,
            passed_count=passed_count,
            failed_count=failed_count,
            total_count=total_count,
            stdout=cmd_rec.output or "",
            stderr=cmd_rec.error_details or "",
            duration_ms=cmd_rec.duration_ms,
            failure_details=failure_details[:5]
        )

        mission_state_manager.record_test_result(task_id, test_record)

        if is_success:
            self.dispatch_event(
                task_id=task_id,
                recipient="shadow_council",
                event_type="test_success",
                content=f"All checks passed successfully! Exit code: 0, Total: {total_count}, Passed: {passed_count}. Handing off to Shadow Council for code and security review.",
                evidence=f"Command: {test_command}\nExit code: {exit_code}\nOutput summary:\n{raw_output[-300:]}"
            )
            # Update criteria
            for cr in mission.acceptance_criteria:
                if "test" in cr.description.lower():
                    cr.status = CriterionStatus.PASS
                    cr.evidence = f"Passed check '{test_command}' with exit code 0."
            mission_state_manager.save_mission(mission)
            return True, test_record
        else:
            self.dispatch_event(
                task_id=task_id,
                recipient="samurai",
                event_type="test_failure",
                content=f"Test check failed with exit code {exit_code}! Failed assertions: {len(failure_details)}. Routing failure report to Samurai for repair.",
                evidence=f"Command: {test_command}\nExit code: {exit_code}\nFailures:\n" + "\n".join(failure_details) if failure_details else raw_output[-500:],
                next_action="diagnose_and_repair"
            )
            for cr in mission.acceptance_criteria:
                if "test" in cr.description.lower():
                    cr.status = CriterionStatus.FAIL
                    cr.evidence = f"Failed check '{test_command}' with exit code {exit_code}."
            mission_state_manager.save_mission(mission)
            return False, test_record
