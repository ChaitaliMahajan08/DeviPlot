import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.agents.sentinel_tester import parse_test_metrics
from backend.app.agents.shadow_council import ShadowCouncilReviewer
from backend.app.models.mission import (
    Mission,
    MissionStatus,
    TestResultRecord,
    AcceptanceCriterion,
    CriterionStatus
)

class TestEvidenceParserRegression(unittest.TestCase):
    def test_parse_unittest_failure(self):
        """Verify that unittest failure parses exact total, passed, and failed counts."""
        stderr_sample = (
            ".F..\n"
            "======================================================================\n"
            "FAIL: test_exact_eighteen_boundary (test_age_validator.TestAgeValidator.test_exact_eighteen_boundary)\n"
            "----------------------------------------------------------------------\n"
            "Traceback (most recent call last):\n"
            "  File \"test_age_validator.py\", line 11, in test_exact_eighteen_boundary\n"
            "    self.assertTrue(is_valid_age(18))\n"
            "AssertionError: False is not true\n\n"
            "----------------------------------------------------------------------\n"
            "Ran 4 tests in 0.003s\n\n"
            "FAILED (failures=1)\n"
        )
        res = parse_test_metrics(stdout="", stderr=stderr_sample, exit_code=1)
        self.assertEqual(res["total_count"], 4)
        self.assertEqual(res["passed_count"], 3)
        self.assertEqual(res["failed_count"], 1)
        self.assertFalse(res["is_success"])
        self.assertTrue(any("FAIL:" in d or "AssertionError" in d for d in res["failure_details"]))

    def test_parse_unittest_success(self):
        """Verify that unittest success parses exact total and passed counts without loss."""
        stderr_sample = (
            "....\n"
            "----------------------------------------------------------------------\n"
            "Ran 4 tests in 0.001s\n\n"
            "OK\n"
        )
        res = parse_test_metrics(stdout="", stderr=stderr_sample, exit_code=0)
        self.assertEqual(res["total_count"], 4)
        self.assertEqual(res["passed_count"], 4)
        self.assertEqual(res["failed_count"], 0)
        self.assertTrue(res["is_success"])
        self.assertEqual(len(res["failure_details"]), 0)

    def test_zero_tests_rejected_as_failure(self):
        """
        CRITICAL REGRESSION REQUIREMENT:
        If test runner reports zero executed tests even with exit code 0,
        it MUST be rejected and never inferred as success.
        """
        stderr_sample = (
            "----------------------------------------------------------------------\n"
            "Ran 0 tests in 0.000s\n\n"
            "OK\n"
        )
        res = parse_test_metrics(stdout="", stderr=stderr_sample, exit_code=0)
        self.assertEqual(res["total_count"], 0)
        self.assertEqual(res["passed_count"], 0)
        self.assertFalse(res["is_success"], "Zero tests executed must NEVER be treated as successful!")
        self.assertTrue(any("Zero tests executed" in d for d in res["failure_details"]))

    def test_parse_pytest_breakdown(self):
        """Verify pytest output format breakdown."""
        sample = "==== 5 passed, 2 failed in 0.45s ===="
        res = parse_test_metrics(stdout=sample, stderr="", exit_code=1)
        self.assertEqual(res["total_count"], 7)
        self.assertEqual(res["passed_count"], 5)
        self.assertEqual(res["failed_count"], 2)
        self.assertFalse(res["is_success"])

    def test_shadow_council_rejects_zero_tests(self):
        """Verify Shadow Council refuses to approve a change when 0 tests were executed."""
        from backend.app.core.state_manager import mission_state_manager
        from backend.app.config import DATA_DIR
        isolated_ws = DATA_DIR / "workspaces" / "test_sc_zero_ws"
        isolated_ws.mkdir(parents=True, exist_ok=True)
        
        reviewer = ShadowCouncilReviewer()
        mission = Mission(
            task_id="test_sc_zero",
            user_request="Refactor module",
            workspace_path=str(isolated_ws),
            status=MissionStatus.REVIEWING,
            test_results=[
                TestResultRecord(
                    id="t1",
                    command="python -m unittest",
                    exit_code=0,
                    passed_count=0,
                    failed_count=0,
                    total_count=0,
                    stdout="",
                    stderr="Ran 0 tests\n\nOK"
                )
            ]
        )
        mission_state_manager.save_mission(mission)
        approved, sec_findings, qual_findings = reviewer.review_mission_changes(mission)
        self.assertFalse(approved, "Shadow Council must reject review when 0 tests executed.")
        self.assertTrue(any("0 executed tests" in f.description for f in qual_findings))

    def test_shadow_council_rejects_failing_tests(self):
        """Verify Shadow Council refuses to approve a change when tests failed."""
        from backend.app.core.state_manager import mission_state_manager
        from backend.app.config import DATA_DIR
        isolated_ws = DATA_DIR / "workspaces" / "test_sc_fail_ws"
        isolated_ws.mkdir(parents=True, exist_ok=True)

        reviewer = ShadowCouncilReviewer()
        mission = Mission(
            task_id="test_sc_fail",
            user_request="Refactor module",
            workspace_path=str(isolated_ws),
            status=MissionStatus.REVIEWING,
            test_results=[
                TestResultRecord(
                    id="t1",
                    command="python -m unittest",
                    exit_code=1,
                    passed_count=2,
                    failed_count=1,
                    total_count=3,
                    stdout="",
                    stderr="FAILED (failures=1)"
                )
            ]
        )
        mission_state_manager.save_mission(mission)
        approved, sec_findings, qual_findings = reviewer.review_mission_changes(mission)
        self.assertFalse(approved, "Shadow Council must reject review when tests failed.")
        self.assertTrue(any("Test runner exited with code 1" in f.description for f in qual_findings))

if __name__ == "__main__":
    unittest.main()
