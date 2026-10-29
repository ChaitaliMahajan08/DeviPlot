# DevPilot: The Mystic Mikado’s Autonomous AI Engineering Guild

> **PECathon 2026 — Problem Statement PS-001 Implementation**  
> *“Plan like a Shogun. Build like a Samurai. Test like a Sentinel. Adapt until the mission is complete.”*

---

## 1. Executive Summary & Purpose

DevPilot is an autonomous multi-agent software engineering guild designed to transform natural-language requirements into working, tested, independently verified, and security-reviewed modifications to software repositories.

Rather than acting as a superficial chatbot or role prompt, DevPilot operates as a deterministic, evidence-driven engineering guild with:
- **Formal Agent Roles**: Shogun (Planner), Samurai (Developer), Sentinel (Tester & Verifier), and Shadow Council (Security & Quality Reviewer).
- **Adaptive Closed-Loop Repair**: Real test failures and AST/diff security alerts trigger bounded correction cycles back to the developer agent.
- **Evidence-Backed Verification**: Zero fabricated test passes; every claim corresponds to actual subprocess exit codes (`0` vs `1`), captured stdout/stderr, and filesystem-verified modifications.
- **Process Sandboxing**: Path traversal guards, command policy blacklists (`rm -rf`, `format`, `mkfs`, force pushes), secret masking, and human approval gates for consequential operations.
- **The Engineer's Atelier UI**: A distinctive interface honoring editorial drafting-paper aesthetics (`#F3F0E7`, `#242820`, `#244FE5`, `#20241F`) with real-time Server-Sent Events (SSE) streaming.

---

## 2. Multi-Agent Guild Architecture

```
                                  [ User Request ]
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    Agent A — Shogun (The Planner)    │
                      │  • Reconnaissance & File Inspection  │
                      │  • Ambiguity Detection               │
                      │  • Formulate Acceptance Criteria     │
                      │  • Task Decomposition & Dependency   │
                      └──────────────────┬───────────────────┘
                                         │ Plan & Criteria
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    Agent E — Guild Orchestrator      │
                      │  • State Machine Lifecycle Owner     │
                      │  • Shared State Persistence (JSON)   │
                      │  • Event Bus & SSE Broadcast         │
                      └──────────────┬────────────────┬──────┘
                                     │                │
                      Task Hand-off  │                │ Test Directives
                                     ▼                ▼
┌──────────────────────────────────────┐            ┌──────────────────────────────────────┐
│   Agent B — Samurai (The Craftsman)  │◄───────────┤   Agent C — Sentinel (The Tester)    │
│  • Context Search & File Inspection  │  Failure   │  • Test Harness Discovery            │
│  • Verified Filesystem Edits         │  Feedback  │  • Real Process Execution (Exit Code)│
│  • Git Diff Generation               │    Loop    │  • Failure Diagnosis & Handoff       │
└──────────────────┬───────────────────┘ (Retries≤2)└──────────────────┬───────────────────┘
                   │                                                   │
                   │ Diff & Artifacts                                  │ Tests Passed
                   └─────────────────────────┬─────────────────────────┘
                                             ▼
                      ┌──────────────────────────────────────┐
                      │ Agent D — Shadow Council (Reviewer)  │
                      │  • Credential & Secret Scanner       │
                      │  • AST & Dangerous Pattern Detection │
                      │  • Code Maintainability & Regressions│
                      └──────────────────┬───────────────────┘
                                         │
                        Risk Detected?   ├───────────────┐ Consequential Action
                                         ▼               ▼
                      ┌─────────────────────┐ ┌──────────────────────────────────────┐
                      │ Remediate / Re-test │ │      Human Approval Gate (Modal)     │
                      └─────────────────────┘ └──────────────────┬───────────────────┘
                                                                 │ Approved
                                                                 ▼
                                              ┌──────────────────────────────────────┐
                                              │ Final Evidence-Backed Mission Report │
                                              │ (VERIFIED / PARTIALLY_VERIFIED/FAIL) │
                                              └──────────────────────────────────────┘
```

---

## 3. Agent Roles & Responsibilities

| Agent | Guild Role | Responsibilities | Core Tool Invocation |
| :--- | :--- | :--- | :--- |
| **Shogun** | Guild Master / Strategic Planner | Repository reconnaissance, ambiguity refusal (`NEEDS_CLARIFICATION`), measurable acceptance criteria, task decomposition, and final outcome cross-examination. | `list_files`, `search_files` |
| **Samurai** | Master Craftsman / Developer | File reading before editing, context-aware minimal diffs, atomic filesystem writes, verified disk presence, targeted repair of diagnostic test failures. | `read_file`, `write_file`, `edit_file`, `git_diff` |
| **Sentinel** | Tester & Independent Verifier | Harness discovery (`unittest`, `pytest`, `npm test`), execution of real subprocesses, exit code capture, failure traceback isolation, criterion validation. | `run_command` (sandboxed with timeout) |
| **Shadow Council** | Security & Code Review | Unified diff and source file scanning for leaked credentials (AWS, OpenAI, GitHub tokens), AST dangerous patterns (`eval()`, `exec()`, injection), human approval requests. | `scan_text_for_security_issues`, `git_diff` |
| **Orchestrator** | Guild Core Coordination | State machine transitions, bounded retries (`retry_count <= max_retries`), inter-agent message routing, persistence to `.devpilot/missions/`. | `MissionStateManager`, `MissionEventBus` |

---

## 4. State Machine Lifecycle & Transitions

DevPilot enforces a bounded, deterministic state machine:

1. **`QUEUED`**: Mission initialized with unique ID (`msn_xxxxxxxx`) and registered in state manager.
2. **`PLANNING`**: Shogun conducts reconnaissance and evaluates user prompt clarity.
   - *Transition to `NEEDS_CLARIFICATION`* if prompt is ambiguous or lacks actionable intent.
3. **`IMPLEMENTING`**: Samurai investigates context and applies verified file edits.
4. **`TESTING`**: Sentinel discovers and runs automated test suites.
   - *Failure Branch $\to$ `RETRYING`*: Sentinel extracts failure traceback and routes to Samurai for repair (bounded to `max_retries`, default: 2).
   - *Repeated Failure Branch $\to$ `FAILED`*: Honest report generation when retries are exhausted.
5. **`REVIEWING`**: Shadow Council audits diffs and workspace files.
   - *Sensitive Alert Branch $\to$ `WAITING_FOR_APPROVAL`*: Execution halted pending human decision.
6. **`VERIFIED`**: All criteria satisfied, zero tests failed, clean security audit.

---

## 5. Security & Safety Sandbox Controls

Safety is strictly enforced on the backend, not merely rendered in the UI:
- **Path Containment Guard**: Every file operation verifies `Path(target).resolve().relative_to(workspace_root)`. Traversal attempts (e.g., `../../etc/passwd`) immediately raise a `SecurityViolation` and are recorded as `BLOCKED`.
- **Command Policy Blacklist**: Commands containing `rm -rf /`, `rmdir /s /q c:\`, `format `, `mkfs`, `git push --force`, or destructive reset flags are blocked before process spawning.
- **Process Boundaries**: Subprocesses execute with an enforced 45-second timeout and output character caps to prevent infinite loops or memory exhaustion.
- **Secret Masking & Scanner**: Real-time regex matching automatically masks API keys (`sk-...`, `AIza...`, `ghp_...`, RSA private keys) in stdout, stderr, and unified diffs.
- **Human Approval Gate**: Sensitive or consequential actions require explicit operator sign-off via `/api/missions/<id>/approvals/<request_id>`.

---

## 6. The 5 Evaluation Scenarios

DevPilot includes 5 reproducible fixtures in `backend/fixtures/` and an automated test suite in `tests/test_scenarios_all.py`:

| Scenario | Objective | Demonstrated Behavior |
| :--- | :--- | :--- |
| **Scenario A: Feature Implementation** | Add `calculate_fibonacci(n)` to existing `math_utils.py`. | Shogun inspects existing functions, Samurai adds minimal implementation preserving existing behavior, adds unit tests, Sentinel passes suite with exit code 0. |
| **Scenario B: Seeded Bug Fix** | Correct VIP discount logic in `discount_service.py`. | Samurai inspects failing assertions, applies targeted mathematical calculation patch, Sentinel verifies test suite passes. |
| **Scenario C: Test-Driven Recovery** | Boundary condition bug in `age_validator.py`. | **Initial test fails with exit code 1**. Failure traceback transferred to Samurai. Samurai repairs `age > 18` to `age >= 18`. Sentinel re-runs and **passes on second run**. |
| **Scenario D: Security & Code Review** | Dangerous `eval()` in `expression_evaluator.py`. | Shadow Council detects `eval()`, issues CRITICAL alert, triggers human gate/remediation, Samurai refactors to `ast.literal_eval()`, verified by re-review. |
| **Scenario E: Unexpected Condition** | Ambiguous prompt `"do something"`. | Shogun detects lack of actionable criteria, transitions cleanly to `NEEDS_CLARIFICATION` / `FAILED` rather than pretending success. |

---

## 7. Setup & Execution Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Git 2.20+
- Modern Web Browser (Chrome, Edge, Firefox, Safari)

### Installation
Clone the repository:
```bash
git clone https://github.com/ChaitaliMahajan08/DeviPlot.git
cd Deviplot
```

Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

### Running the Application
Launch the unified DevPilot server (API + The Engineer's Atelier UI):
```bash
python run.py
```
Open **`http://localhost:5000`** in your browser.

### Running the Evaluation Demonstration (CLI)
Run the automated Scenario C Test-Driven Recovery showcase directly in terminal:
```bash
python scripts/run_demo.py
```

### Running Full Automated Test Suite
Verify all 5 evaluation scenarios and state machine transitions:
```bash
python -m unittest tests/test_scenarios_all.py
```

---

## 8. API Contract Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/missions` | Create and optionally start a new autonomous mission (`{user_request, workspace_path, max_retries}`). |
| `GET` | `/api/missions` | Retrieve mission history and run states. |
| `GET` | `/api/missions/<task_id>` | Retrieve full structured state for a specific mission. |
| `GET` | `/api/missions/<task_id>/events` | Server-Sent Events (SSE) live stream of agent handoffs, tool calls, and status changes. |
| `POST` | `/api/missions/<task_id>/approvals/<req_id>` | Submit human operator decision (`{approved: true/false}`). |
| `POST` | `/api/missions/<task_id>/cancel` | Halt an active mission run. |
| `GET` | `/api/workspaces` | List available project workspaces and evaluation fixtures. |
| `POST` | `/api/workspaces/reset-fixture` | Reset a fixture to fresh state for reproducible testing. |
| `GET` | `/api/workspaces/files` | File tree listing for Repository Explorer. |
| `GET` | `/api/workspaces/file-content` | Read source file contents for code inspector. |

---

## 9. Implementation Status Matrix

- [x] **Agent A — Shogun (Planner)**: Reconnaissance, acceptance criteria, task breakdown, ambiguity refusal.
- [x] **Agent B — Samurai (Developer)**: Context search, file reading, bounded modifications, filesystem verification.
- [x] **Agent C — Sentinel (Tester & Verifier)**: Real process execution, exit code capture, traceback diagnosis, independent verification.
- [x] **Agent D — Shadow Council (Security Reviewer)**: Credential scan, AST pattern checks, diff audit, approval trigger.
- [x] **Agent E — Guild Orchestrator**: Deterministic state machine, bounded retries (<=2), persistent JSON storage, loop prevention.
- [x] **Shared Mission State & Event Bus**: Pydantic models, persistent mission records, real-time SSE streaming.
- [x] **Tool Registry & Security Sandbox**: Path containment, command blacklisting, process timeouts, secret masking.
- [x] **Engineer's Atelier Frontend**: 6 functional views, drafting-paper aesthetics, live SSE updates, diff viewer, test matrix, approval modal.
- [x] **5 Evaluation Scenarios**: Feature Addition, Seeded Bug, Test-Driven Recovery, Security Audit, Ambiguity Refusal.
- [x] **Automated Test Suite**: 100% passing tests for all 5 scenarios.
- [x] **Git Remote Integration**: Clean atomic commits pushed to `https://github.com/ChaitaliMahajan08/DeviPlot`.

---

## 10. License & Credits

Developed for **PECathon 2026 Problem Statement PS-001**.  
Built by the **DevPilot Guild Engineering Team**.
