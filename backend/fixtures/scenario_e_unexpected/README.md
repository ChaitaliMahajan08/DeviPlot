# Scenario E: Unexpected Condition & Transparent Handling

This test fixture is designed to demonstrate:
1. Ambiguous requirements detection (e.g. "fix it" or "asdf").
2. Explicit state transition to `NEEDS_CLARIFICATION`.
3. Bounded retries stopping after limit is reached.
4. Blocked dangerous operations (e.g. `rm -rf /` or path traversal `../../`).
5. Never pretending success when verification fails.
