import os
import sys
import shutil
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.core.orchestrator import guild_orchestrator
from backend.app.models.mission import MissionStatus, CriterionStatus, VerificationOutcome
from backend.app.config import FIXTURES_DIR, DATA_DIR

class TestAllEvaluationScenarios(unittest.TestCase):
    def setUp(self):
        self.test_workspace = DATA_DIR / "workspaces" / "test_run_all"
        if self.test_workspace.exists():
            shutil.rmtree(self.test_workspace)
        self.test_workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_workspace.exists():
            shutil.rmtree(self.test_workspace)

    def test_scenario_a_feature_implementation(self):
        """
        SCENARIO A — FEATURE IMPLEMENTATION:
        Request adding calculate_fibonacci(n) to math_utils.
        Show repository inspection, acceptance criteria, implementation, tests, review, and final report.
        """
        src_dir = FIXTURES_DIR / "scenario_a_feature"
        for item in src_dir.iterdir():
            if item.is_file():
                shutil.copy(item, self.test_workspace / item.name)

        mission = guild_orchestrator.create_mission(
            user_request="Add feature calculate_fibonacci(n) to math_utils and verify with tests.",
            workspace_path=str(self.test_workspace),
            max_retries=2
        )

        finished_mission = guild_orchestrator.execute_mission(mission.task_id)

        self.assertEqual(finished_mission.status, MissionStatus.VERIFIED)
        self.assertIn("math_utils.py", finished_mission.changed_files)
        self.assertGreaterEqual(len(finished_mission.test_results), 1)
        self.assertEqual(finished_mission.test_results[-1].exit_code, 0)
        self.assertIsNotNone(finished_mission.final_verification)
        self.assertEqual(finished_mission.final_verification.outcome, VerificationOutcome.VERIFIED)
        print("\nScenario A (Feature Implementation) passed!")

    def test_scenario_b_seeded_bug_fix(self):
        """
        SCENARIO B — SEEDED BUG:
        Fix the seeded bug in discount_service where VIP tier calculation returns full price.
        """
        src_dir = FIXTURES_DIR / "scenario_b_bug"
        for item in src_dir.iterdir():
            if item.is_file():
                shutil.copy(item, self.test_workspace / item.name)

        mission = guild_orchestrator.create_mission(
            user_request="Fix the bug in discount_service where VIP discount fails assertions.",
            workspace_path=str(self.test_workspace),
            max_retries=2
        )

        finished_mission = guild_orchestrator.execute_mission(mission.task_id)

        self.assertEqual(finished_mission.status, MissionStatus.VERIFIED)
        self.assertIn("discount_service.py", finished_mission.changed_files)
        self.assertEqual(finished_mission.test_results[-1].exit_code, 0)
        self.assertIsNotNone(finished_mission.final_verification)
        self.assertEqual(finished_mission.final_verification.outcome, VerificationOutcome.VERIFIED)
        print("\nScenario B (Seeded Bug) passed!")

    def test_scenario_c_test_driven_recovery(self):
        """SCENARIO C — TEST-DRIVEN RECOVERY: initial failing test -> failure diagnosis -> targeted repair -> rerun -> pass"""
        src_dir = FIXTURES_DIR / "scenario_c_recovery"
        for item in src_dir.iterdir():
            if item.is_file():
                shutil.copy(item, self.test_workspace / item.name)

        mission = guild_orchestrator.create_mission(
            user_request="Fix boundary bug in age_validator so that age 18 passes test_exact_eighteen_boundary.",
            workspace_path=str(self.test_workspace),
            max_retries=2
        )

        finished_mission = guild_orchestrator.execute_mission(mission.task_id)

        self.assertEqual(finished_mission.status, MissionStatus.VERIFIED)
        self.assertGreaterEqual(len(finished_mission.test_results), 2)
        self.assertEqual(finished_mission.retry_count, 1)
        
        # Verify genuine test metrics on both runs
        first_run = finished_mission.test_results[0]
        final_run = finished_mission.test_results[-1]
        
        self.assertEqual(first_run.exit_code, 1)
        self.assertEqual(first_run.total_count, 4)
        self.assertEqual(first_run.passed_count, 3)
        self.assertEqual(first_run.failed_count, 1)
        
        self.assertEqual(final_run.exit_code, 0)
        self.assertEqual(final_run.total_count, 4)
        self.assertEqual(final_run.passed_count, 4)
        self.assertEqual(final_run.failed_count, 0)
        print("\nScenario C (Test-Driven Recovery) passed!")

    def test_scenario_d_security_review(self):
        """SCENARIO D — SECURITY & CODE REVIEW: Shadow Council flags eval vulnerability and forces remediation"""
        src_dir = FIXTURES_DIR / "scenario_d_security"
        for item in src_dir.iterdir():
            if item.is_file():
                shutil.copy(item, self.test_workspace / item.name)

        mission = guild_orchestrator.create_mission(
            user_request="Refactor expression_evaluator to eliminate unsafe eval vulnerability while keeping basic literal evaluation working.",
            workspace_path=str(self.test_workspace),
            max_retries=2
        )

        finished_mission = guild_orchestrator.execute_mission(mission.task_id)
        self.assertGreaterEqual(len(finished_mission.security_findings), 1)
        print("\nScenario D (Security Review) passed!")

    def test_scenario_e_unexpected_condition(self):
        """SCENARIO E — UNEXPECTED CONDITION: Ambiguous or invalid request triggers honest refusal"""
        mission = guild_orchestrator.create_mission(
            user_request="do something",
            workspace_path=str(self.test_workspace),
            max_retries=2
        )
        finished_mission = guild_orchestrator.execute_mission(mission.task_id)
        self.assertEqual(finished_mission.status, MissionStatus.FAILED)
        print("\nScenario E (Unexpected Condition) passed!")

if __name__ == "__main__":
    unittest.main()
