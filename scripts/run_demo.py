import os
import sys
import time
import shutil
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.core.orchestrator import guild_orchestrator
from backend.app.core.state_manager import mission_state_manager
from backend.app.config import FIXTURES_DIR, DATA_DIR

def run_demonstration():
    print("=" * 70)
    print("   DEVPILOT: PECATHON 2026 PS-001 DEMONSTRATION")
    print("   The Mystic Mikado's Autonomous AI Engineering Guild")
    print("=" * 70)
    
    # Run Scenario C: Test-Driven Recovery
    print("\n>>> DEMONSTRATING SCENARIO C: TEST-DRIVEN RECOVERY")
    print("Goal: Start with a reproducible failing boundary test, transfer diagnostic")
    print("      evidence to Samurai, apply targeted fix, rerun tests via Sentinel,")
    print("      and verify with Shadow Council.")
    
    demo_ws = DATA_DIR / "workspaces" / "demo_run_scenario_c"
    if demo_ws.exists():
        shutil.rmtree(demo_ws)
    demo_ws.mkdir(parents=True, exist_ok=True)
    
    src = FIXTURES_DIR / "scenario_c_recovery"
    for item in src.iterdir():
        if item.is_file():
            shutil.copy(item, demo_ws / item.name)

    print(f"\n[1] Initialized demo workspace: {demo_ws}")
    print("[2] Dispatching mission to Guild Orchestrator...")
    
    mission = guild_orchestrator.create_mission(
        user_request="Fix boundary bug in age_validator so that age 18 passes test_exact_eighteen_boundary.",
        workspace_path=str(demo_ws),
        max_retries=2
    )

    t0 = time.time()
    finished = guild_orchestrator.execute_mission(mission.task_id)
    duration = time.time() - t0

    print(f"\n[3] Execution completed in {duration:.2f} seconds!")
    print(f"    - Mission ID:    {finished.task_id}")
    print(f"    - Final Status:  {finished.status.value}")
    print(f"    - Retries Count: {finished.retry_count}")
    print(f"    - Changed Files: {', '.join(finished.changed_files)}")

    print("\n[4] Acceptance Criteria Status:")
    for c in finished.acceptance_criteria:
        print(f"    * [{c.status.value}] {c.id}: {c.description}")
        if c.evidence:
            print(f"      Evidence: {c.evidence}")

    print("\n[5] Test Execution Evidence:")
    for idx, tr in enumerate(finished.test_results, 1):
        status_label = "FAILED (Expected)" if tr.exit_code != 0 else "PASSED"
        print(f"    Run #{idx} [{status_label}]: Exit Code {tr.exit_code} | Passed: {tr.passed_count}/{tr.total_count} | Failed: {tr.failed_count} ({tr.duration_ms}ms)")
        print(f"      Command: `{tr.command}`")
        if tr.failure_details:
            print(f"      Diagnostic: {tr.failure_details[0]}")
        else:
            print(f"      Diagnostic: All {tr.passed_count} test assertions satisfied.")

    print("\n[6] Shadow Council Review:")
    print(f"    - Security alerts: {len(finished.security_findings)}")
    print(f"    - Quality alerts:  {len(finished.review_findings)}")

    print("\n[7] Final Verified Report:")
    if finished.final_verification:
        print(f"    - Outcome: {finished.final_verification.outcome.value}")
        print(f"    - Summary: {finished.final_verification.summary}")

    print("\n" + "=" * 70)
    print("   DEMONSTRATION COMPLETE: GENUINE MULTI-AGENT ADAPTIVE EXECUTION")
    print("=" * 70)

if __name__ == "__main__":
    run_demonstration()
