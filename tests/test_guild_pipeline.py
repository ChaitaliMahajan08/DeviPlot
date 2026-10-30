import os
import sys
import shutil
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.core.orchestrator import guild_orchestrator
from backend.app.core.state_manager import mission_state_manager
from backend.app.models.mission import MissionStatus, CriterionStatus, VerificationOutcome
from backend.app.config import FIXTURES_DIR, DATA_DIR

class TestDevPilotGuildPipeline(unittest.TestCase):
    def setUp(self):
        self.test_workspace = DATA_DIR / "workspaces" / "test_run_unit"
        if self.test_workspace.exists():
            shutil.rmtree(self.test_workspace)
        self.test_workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_workspace.exists():
            shutil.rmtree(self.test_workspace)

    def test_scenario_c_test_driven_recovery(self):
        """
        Verify that Sentinel detects initial failing test, hands off failure details
        to Samurai, Samurai repairs boundary logic, and Sentinel re-tests and passes!
        """
        # Copy fixture C into test workspace
        src_dir = FIXTURES_DIR / "scenario_c_recovery"
        for item in src_dir.iterdir():
            if item.is_file():
                shutil.copy(item, self.test_workspace / item.name)

        # Create mission
        mission = guild_orchestrator.create_mission(
            user_request="Fix test failure in test_age_validator so that age 18 is recognized as legal adult age.",
            workspace_path=str(self.test_workspace),
            max_retries=2
        )

        # Execute mission
        finished_mission = guild_orchestrator.execute_mission(mission.task_id)

        # Assertions
        self.assertEqual(finished_mission.status, MissionStatus.VERIFIED)
        self.assertGreaterEqual(len(finished_mission.test_results), 2, "Must execute initial test run and re-test after repair")
        self.assertEqual(finished_mission.retry_count, 1, "Should have performed exactly 1 repair retry")
        
        # Verify first test failed (3 passed, 1 failed, total 4) and second test passed (4 passed, 0 failed, total 4)
        first_run = finished_mission.test_results[0]
        final_run = finished_mission.test_results[-1]
        
        self.assertNotEqual(first_run.exit_code, 0)
        self.assertEqual(first_run.total_count, 4, "Initial run must discover and execute 4 tests")
        self.assertEqual(first_run.passed_count, 3, "Initial run should have 3 passed tests")
        self.assertEqual(first_run.failed_count, 1, "Initial run should have exactly 1 failing test")
        
        self.assertEqual(final_run.exit_code, 0)
        self.assertEqual(final_run.total_count, 4, "Second run must discover and execute 4 tests")
        self.assertEqual(final_run.passed_count, 4, "Second run should have all 4 passed tests")
        self.assertEqual(final_run.failed_count, 0, "Second run should have 0 failing tests")
        
        # Verify acceptance criteria
        self.assertTrue(all(c.status == CriterionStatus.PASS for c in finished_mission.acceptance_criteria))
        
        # Verify final report
        self.assertIsNotNone(finished_mission.final_verification)
        self.assertEqual(finished_mission.final_verification.outcome, VerificationOutcome.VERIFIED)
        print("\nScenario C (Test-Driven Recovery) verified successfully!")

    def test_scenario_d_security_audit(self):
        """
        Verify that Shadow Council flags dangerous eval usage and forces remediation.
        """
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
        
        # Should detect security alerts
        self.assertGreaterEqual(len(finished_mission.security_findings), 1)
        self.assertEqual(finished_mission.security_findings[0].category, "security")
        print("\nScenario D (Security Review) verified successfully!")

    def test_scenario_e_ambiguous_request(self):
        """
        Verify that Shogun halts on ambiguous request instead of fabricating fake success.
        """
        mission = guild_orchestrator.create_mission(
            user_request="do something",
            workspace_path=str(self.test_workspace),
            max_retries=2
        )
        finished_mission = guild_orchestrator.execute_mission(mission.task_id)
        
        self.assertEqual(finished_mission.status, MissionStatus.FAILED)
        self.assertIn("Clarification required", finished_mission.final_verification.summary)
        print("\nScenario E (Ambiguous Request) verified successfully!")

if __name__ == "__main__":
    unittest.main()
