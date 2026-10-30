import uuid
from typing import List, Tuple
from .base import BaseAgent
from ..models.mission import (
    Mission,
    ReviewFinding,
    ReviewSeverity,
    HumanApprovalRequest,
    CriterionStatus
)
from ..core.state_manager import mission_state_manager
from ..tools.security_scanner import scan_text_for_security_issues

class ShadowCouncilReviewer(BaseAgent):
    def __init__(self):
        super().__init__(
            name="shadow_council",
            role="Security & Code Quality Council",
            title="Vigilant Inspector of Vulnerabilities and Code Health"
        )

    def review_mission_changes(self, mission: Mission) -> Tuple[bool, List[ReviewFinding], List[ReviewFinding]]:
        task_id = mission.task_id
        workspace = mission.workspace_path

        self.dispatch_event(
            task_id=task_id,
            recipient="orchestrator",
            event_type="review_start",
            content="Shadow Council initiated code and security review of workspace diff..."
        )

        # 1. Fetch current git diff
        diff_rec = self.call_tool(task_id=task_id, workspace=workspace, tool_name="git_diff", arguments={})
        diff_text = diff_rec.output or ""

        # 2. Run security scan on diff AND modified / source files in workspace
        security_findings: List[ReviewFinding] = []
        
        # Scan diff
        if diff_text:
            diff_sec = scan_text_for_security_issues(diff_text, file_path="workspace_diff")
            security_findings.extend(diff_sec)

        # Also scan workspace python source files for existing vulnerabilities
        from pathlib import Path
        ws_path = Path(workspace)
        for py_p in ws_path.rglob("*.py"):
            if ".devpilot" in py_p.parts or ".git" in py_p.parts:
                continue
            rel_str = str(py_p.relative_to(ws_path)).replace("\\", "/")
            try:
                with open(py_p, "r", encoding="utf-8", errors="ignore") as f:
                    file_content = f.read()
                file_sec = scan_text_for_security_issues(file_content, file_path=rel_str)
                for fs in file_sec:
                    if not any(existing.id == fs.id for existing in security_findings):
                        security_findings.append(fs)
            except Exception:
                continue

        # 3. Code Quality / Style checks on diff
        quality_findings: List[ReviewFinding] = []
        for line_no, line in enumerate(diff_text.split("\n"), 1):
            if line.startswith("+") and not line.startswith("+++"):
                added_code = line[1:].strip()
                # Check for TODO / FIXME / debugging prints
                if "print(" in added_code and "test" not in diff_text.lower():
                    quality_findings.append(ReviewFinding(
                        id=f"qual_print_{uuid.uuid4().hex[:6]}",
                        severity=ReviewSeverity.LOW,
                        category="style",
                        file_path="diff",
                        line_number=line_no,
                        description="Console print statement introduced into production source code.",
                        fix_suggestion="Use structured logging (logger.info or logger.debug) instead of stdout print.",
                        resolved=False
                    ))
                if "TODO" in added_code or "FIXME" in added_code:
                    quality_findings.append(ReviewFinding(
                        id=f"qual_todo_{uuid.uuid4().hex[:6]}",
                        severity=ReviewSeverity.INFO,
                        category="maintainability",
                        file_path="diff",
                        line_number=line_no,
                        description="Unresolved TODO / FIXME marker in newly introduced code.",
                        fix_suggestion="Implement the missing logic or track as an explicit issue before finalizing.",
                        resolved=False
                    ))

        # 4. Independent Test Evidence Verification
        test_evidence_findings: List[ReviewFinding] = []
        if not mission.test_results:
            test_evidence_findings.append(ReviewFinding(
                id=f"test_none_{uuid.uuid4().hex[:6]}",
                severity=ReviewSeverity.CRITICAL,
                category="verification",
                file_path="test_suite",
                line_number=None,
                description="Independent Verification Failure: No automated test results recorded for mission.",
                fix_suggestion="Execute targeted automated tests before requesting Shadow Council review.",
                resolved=False
            ))
        else:
            last_test = mission.test_results[-1]
            if last_test.total_count == 0:
                test_evidence_findings.append(ReviewFinding(
                    id=f"test_zero_{uuid.uuid4().hex[:6]}",
                    severity=ReviewSeverity.CRITICAL,
                    category="verification",
                    file_path=last_test.command,
                    line_number=None,
                    description=f"Independent Verification Failure: Latest test run '{last_test.command}' reported 0 executed tests.",
                    fix_suggestion="Ensure test discovery finds valid test cases and executes them.",
                    resolved=False
                ))
            elif last_test.exit_code != 0 or last_test.failed_count > 0:
                test_evidence_findings.append(ReviewFinding(
                    id=f"test_failed_{uuid.uuid4().hex[:6]}",
                    severity=ReviewSeverity.CRITICAL,
                    category="verification",
                    file_path=last_test.command,
                    line_number=None,
                    description=f"Independent Verification Failure: Test runner exited with code {last_test.exit_code} ({last_test.failed_count}/{last_test.total_count} failed).",
                    fix_suggestion="Resolve failing assertions before requesting final review.",
                    resolved=False
                ))

        quality_findings.extend(test_evidence_findings)

        # Record findings
        mission_state_manager.record_review_findings(task_id, quality_findings, is_security=False)
        mission_state_manager.record_review_findings(task_id, security_findings, is_security=True)

        # Critical security check: if CRITICAL or HIGH security finding found
        critical_security = [f for f in security_findings if f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH)]

        if critical_security:
            first_crit = critical_security[0]
            # Create human approval request if safety boundary is crossed
            approval_req = HumanApprovalRequest(
                id=f"appr_{uuid.uuid4().hex[:8]}",
                action_type="security_alert_approval",
                description=f"Security alert: {first_crit.description}",
                details={
                    "severity": first_crit.severity.value,
                    "remediation": first_crit.fix_suggestion,
                    "target_file": first_crit.file_path,
                    "line": first_crit.line_number
                }
            )
            mission_state_manager.record_approval_request(task_id, approval_req)

            self.dispatch_event(
                task_id=task_id,
                recipient="orchestrator",
                event_type="security_alert",
                content=f"CRITICAL SECURITY ALERT: {first_crit.description}. Execution halted pending human approval or remediation.",
                evidence=f"Severity: {first_crit.severity.value}\nLine {first_crit.line_number}: {first_crit.description}\nFix Suggestion: {first_crit.fix_suggestion}",
                next_action="await_human_decision"
            )

            for cr in mission.acceptance_criteria:
                desc_l = cr.description.lower()
                if any(term in desc_l for term in ("security", "integrity", "credential", "unsafe")):
                    cr.status = CriterionStatus.FAIL
                    cr.evidence = f"Security vulnerability detected: {first_crit.description}"
            mission_state_manager.save_mission(mission)

            return False, security_findings, quality_findings

        if test_evidence_findings:
            first_test_err = test_evidence_findings[0]
            self.dispatch_event(
                task_id=task_id,
                recipient="orchestrator",
                event_type="verification_rejection",
                content=f"INDEPENDENT VERIFICATION REJECTED: {first_test_err.description}",
                evidence=f"Command: {mission.test_results[-1].command if mission.test_results else 'None'}\nPassed: {mission.test_results[-1].passed_count if mission.test_results else 0}/{mission.test_results[-1].total_count if mission.test_results else 0}",
                next_action="remedy_test_defects"
            )
            for cr in mission.acceptance_criteria:
                if "test" in cr.description.lower():
                    cr.status = CriterionStatus.FAIL
                    cr.evidence = first_test_err.description
            mission_state_manager.save_mission(mission)
            return False, security_findings, quality_findings

        # If no critical security or test verification issues
        self.dispatch_event(
            task_id=task_id,
            recipient="orchestrator",
            event_type="review_passed",
            content=f"Shadow Council review passed. 0 critical vulnerabilities, valid test evidence confirmed ({mission.test_results[-1].passed_count}/{mission.test_results[-1].total_count} passing).",
            evidence=f"Scanned {len(diff_text.splitlines())} lines of unified diff and verified exit code 0."
        )

        for cr in mission.acceptance_criteria:
            desc_l = cr.description.lower()
            if any(term in desc_l for term in ("security", "integrity", "credential", "unsafe")):
                cr.status = CriterionStatus.PASS
                cr.evidence = "Security audit confirmed: 0 credentials exposed, safe AST patterns."
        mission_state_manager.save_mission(mission)

        return True, security_findings, quality_findings
