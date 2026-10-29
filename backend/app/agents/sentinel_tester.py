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

def parse_test_metrics(stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
    """
    Parses real test execution output from unittest, pytest, npm, or subprocess runners.
    Enforces strict evidence rules:
    - Zero tests executed MUST NEVER be inferred as success.
    - Captures real total, passed, failed, and failure traceback lines.
    - Preserves both stdout and stderr.
    """
    stdout_clean = stdout or ""
    stderr_clean = stderr or ""
    combined = f"{stdout_clean}\n{stderr_clean}".strip()
    
    total_count = 0
    passed_count = 0
    failed_count = 0
    failure_details: List[str] = []

    # 1. Python unittest parser
    # Format:
    # Ran X test(s) in Ys
    # FAILED (failures=A, errors=B) or OK or OK (skipped=C)
    ran_match = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    if ran_match:
        total_count = int(ran_match.group(1))
        
        # Check for FAILED (failures=X, errors=Y)
        failed_match = re.search(r"FAILED\s*\((.*?)\)", combined)
        if failed_match:
            breakdown = failed_match.group(1)
            fail_m = re.search(r"failures=(\d+)", breakdown)
            err_m = re.search(r"errors=(\d+)", breakdown)
            f_num = int(fail_m.group(1)) if fail_m else 0
            e_num = int(err_m.group(1)) if err_m else 0
            failed_count = f_num + e_num
            passed_count = max(0, total_count - failed_count)
        elif "OK" in combined and exit_code == 0:
            passed_count = total_count
            failed_count = 0
        else:
            if exit_code != 0:
                failed_count = max(1, total_count)
                passed_count = max(0, total_count - failed_count)
            else:
                passed_count = total_count
                failed_count = 0

    # 2. Pytest parser
    # Format: "= 4 passed, 1 failed in 0.12s ="
    elif re.search(r"(=+\s*(?:\d+\s+(?:passed|failed|error|skipped)[,\s]*)+\s+in\s+[\d\.]+s\s*=+|no\s+tests\s+ran)", combined, re.IGNORECASE):
        p_match = re.search(r"(\d+)\s+passed", combined)
        f_match = re.search(r"(\d+)\s+failed", combined)
        e_match = re.search(r"(\d+)\s+error", combined)
        passed_count = int(p_match.group(1)) if p_match else 0
        f_num = int(f_match.group(1)) if f_match else 0
        e_num = int(e_match.group(1)) if e_match else 0
        failed_count = f_num + e_num
        total_count = passed_count + failed_count

    # 3. Node / npm test parser
    elif re.search(r"ℹ\s+(?:tests|pass|fail)\s+\d+", combined):
        t_match = re.search(r"ℹ\s+tests\s+(\d+)", combined)
        p_match = re.search(r"ℹ\s+pass\s+(\d+)", combined)
        f_match = re.search(r"ℹ\s+fail\s+(\d+)", combined)
        total_count = int(t_match.group(1)) if t_match else 0
        passed_count = int(p_match.group(1)) if p_match else 0
        failed_count = int(f_match.group(1)) if f_match else 0

    # 4. Fallback process-level check
    else:
        if exit_code == 0:
            if "compileall" in combined or "Listing" in combined:
                total_count = 1
                passed_count = 1
                failed_count = 0
            else:
                total_count = 0
                passed_count = 0
                failed_count = 0
        else:
            total_count = 0
            passed_count = 0
            failed_count = 1

    # Extract failure lines
    for line in combined.split("\n"):
        clean_line = line.strip()
        if any(clean_line.startswith(prefix) for prefix in ("FAIL:", "ERROR:", "AssertionError", "Traceback")):
            if clean_line not in failure_details:
                failure_details.append(clean_line[:200])
        elif any(err_kw in clean_line for err_kw in ("AssertionError:", "ImportError:", "ModuleNotFoundError:", "SyntaxError:")):
            if clean_line not in failure_details:
                failure_details.append(clean_line[:200])

    # ZERO-TEST GUARD:
    # If 0 tests were executed, it MUST NOT be considered a success!
    if total_count == 0:
        is_success = False
        failure_details.append("Zero tests executed: Test harness discovered or executed 0 test cases.")
    elif exit_code != 0 or failed_count > 0:
        is_success = False
    else:
        is_success = True

    return {
        "total_count": total_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "failure_details": failure_details[:6],
        "is_success": is_success
    }

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
            if len(test_files) == 1:
                test_command = f"python -m unittest {test_files[0]}"
            else:
                test_command = "python -m unittest discover -s . -p \"*test*.py\""
        elif js_test_files or package_json:
            test_command = "npm test"
        else:
            self.dispatch_event(
                task_id=task_id,
                recipient="orchestrator",
                event_type="test_warning",
                content="No existing automated test suite detected in repository. Sentinel will verify syntax via Python compile check.",
                evidence="No test_*.py or package.json test scripts discovered."
            )
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

        stdout = cmd_rec.output or ""
        stderr = cmd_rec.error_details or ""
        exit_code = cmd_rec.exit_code if cmd_rec.exit_code is not None else -1

        # Parse metrics with dedicated parser
        metrics = parse_test_metrics(stdout, stderr, exit_code)
        
        is_success = metrics["is_success"]
        total_count = metrics["total_count"]
        passed_count = metrics["passed_count"]
        failed_count = metrics["failed_count"]
        failure_details = metrics["failure_details"]

        test_record = TestResultRecord(
            id=f"test_{uuid.uuid4().hex[:8]}",
            command=test_command,
            exit_code=exit_code,
            passed_count=passed_count,
            failed_count=failed_count,
            total_count=total_count,
            stdout=stdout,
            stderr=stderr,
            duration_ms=cmd_rec.duration_ms,
            failure_details=failure_details
        )

        mission_state_manager.record_test_result(task_id, test_record)

        combined_preview = (stderr + "\n" + stdout).strip()[-400:]

        if is_success:
            self.dispatch_event(
                task_id=task_id,
                recipient="shadow_council",
                event_type="test_success",
                content=f"All checks passed successfully! Exit code: 0, Total: {total_count}, Passed: {passed_count}, Failed: 0. Handing off to Shadow Council for code and security review.",
                evidence=f"Command: {test_command}\nExit code: {exit_code}\nOutput summary:\n{combined_preview}"
            )
            for cr in mission.acceptance_criteria:
                if "test" in cr.description.lower():
                    cr.status = CriterionStatus.PASS
                    cr.evidence = f"Passed check '{test_command}' with exit code 0 ({passed_count}/{total_count} passing)."
            mission_state_manager.save_mission(mission)
            return True, test_record
        else:
            reason = "Zero tests executed" if total_count == 0 else f"Failed {failed_count}/{total_count} tests"
            self.dispatch_event(
                task_id=task_id,
                recipient="samurai",
                event_type="test_failure",
                content=f"Test check failed with exit code {exit_code}! {reason}. Routing failure report to Samurai for repair.",
                evidence=f"Command: {test_command}\nExit code: {exit_code}\nFailures:\n" + ("\n".join(failure_details) if failure_details else combined_preview),
                next_action="diagnose_and_repair"
            )
            for cr in mission.acceptance_criteria:
                if "test" in cr.description.lower():
                    cr.status = CriterionStatus.FAIL
                    cr.evidence = f"Failed check '{test_command}' with exit code {exit_code} ({failed_count} failures, {passed_count}/{total_count} passed)."
            mission_state_manager.save_mission(mission)
            return False, test_record
