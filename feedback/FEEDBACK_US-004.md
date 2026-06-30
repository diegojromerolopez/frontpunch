# FEEDBACK_US-004: Noctifab Tool Evaluation Report

This report evaluates the performance, behavior, and limitations of the `noctifab` tool during the implementation of User Story Four (US-004: Exception Handling & Exponential Backoff Retries) in the `frontpunch` codebase, and proposes concrete recommendations to elevate the tool to Level 4 autonomy.

---

## 1. Summary of Execution

- **Target Specification**: `roadmap/US-004.md` (Exception Handling & Exponential Backoff Retries)
- **Base Branch (Configured)**: `noctifab/feature-US-001-clean` (due to config.yaml value)
- **Base Branch (Actual checkout before run)**: `noctifab/feature-US-003`
- **Result**: **SUCCESS (with regressions)**. The tool completed planning and successfully implemented and validated the exception handling and backoff delay logic on a branch off `noctifab/feature-US-001-clean`. However, because it branched off an outdated base commit, it discarded all changes from US-002 and US-003.

---

## 2. What Went Well

### A. Automatic Plan Decomposition & DAG Generation
- **Successful Parsing**: The tool parsed `roadmap/US-004.md` and decomposed it into a clean, logical 4-task DAG:
  1. `Implement Exponential Backoff Delay Calculation Function` (Success)
  2. `Unit Test Exponential Backoff Formula` (Success)
  3. `Integrate Exception Handling and Retry Logic into Worker` (Success)
  4. `Unit Test Worker's Retry and Dead-Letter Handler` (Success)

### B. Code Generation and Refactoring
- **Clean Implementation**: The Generator successfully implemented `_calculate_backoff_delay`, exception catching in `run()`, and extracted failure handling into a clean `_handle_job_failure` helper.
- **Accurate Tests**: The Tester successfully generated appropriate test files (`tests/unit/test_worker_backoff.py`, `tests/unit/test_retries.py`, `tests/integration/test_worker_integration.py`, `tests/unit/test_worker.py`, and `frontpunch/test_tasks.py`).

### C. Graceful Handling of Non-Fatal Tester Failures
- **Resilient Execution**: The Orchestrator did not crash or block the execution loop when `RunTesterAgent` failed to parse the LLM's output on certain cycles. It logged the failure and proceeded to validation using previously written tests.

---

## 3. What Went Wrong

### A. The "Silent Regression" Base Branch Drift Bug
- **The Issue**: In the committed `.noctifab/config.yaml`, the base branch was configured as `noctifab/feature-US-001-clean`. When the tool was launched, it read this configuration, checked out that old branch, and created `noctifab/feature-US-004` from it.
- **The Consequences**: All files created in US-002 and US-003 (e.g., `frontpunch/cli.py`, `tests/integration/test_client.py`) were deleted in the final branch. The test suite ran and passed, but only with 13 tests instead of the full 34 tests. The tool output `Feature successfully implemented and validated!`, creating a false sense of success.

### B. Tester LLM Formatting & Parsing Crashes on Retries
- **The Issue**: During tasks retries, the Orchestrator appends previous run failures to the Tester's prompt and instructs it to "Fix the tests".
- **The Consequences**: The Gemini model gets confused by the failure logs (which contain python tracebacks and code details) and fails to format its response as a pure JSON block. In Try 2 and Try 3, it returned invalid JSON containing comments (`#`) or unquoted keys (`q:`), causing the Orchestrator's parser to crash with `invalid character '#' looking for beginning of object key string`.

### C. Persistent Git Branch Cache Inheritance
- **The Issue**: If the integration branch (e.g., `noctifab/feature-US-004`) already exists from an aborted run, the Orchestrator checks it out instead of resetting it to the base branch.
- **The Consequences**: In our first run, it inherited duplicate functions and old broken states from a previous execution, causing immediate syntax/compilation conflicts that failed Try 1.

### D. Credentials Failure Finalization Logging
- **The Issue**: PR creation failed with a 401 Unauthorized (`Bad credentials`) error.
- **The Consequences**: The CLI process exited successfully (code 0) and printed `Feature successfully implemented and validated!`, hiding the final integration pipeline failure.

---

## 4. Proposals for Fixes

### A. Fix for Base Branch Drift
- **Recommendation**: Dynamic base branch resolution (like a `git-detect` value). The tool should resolve `base_branch` to the current active checked-out git branch, or query the remote repository's default branch (`main` or `master`) rather than relying on a hardcoded string in the configuration file.

### B. Fix for Tester LLM Formatting & Parsing Crashes
- **Recommendation**: Instead of pasting raw tracebacks directly into the prompt, use a **Log Synthesizer** to extract only structured details (e.g., failed test filename, line number, exception type, expected/actual value).
- **Recommendation**: Configure the LLM client to use **Structured Outputs / JSON Schema Mode** (e.g. `response_mime_type: "application/json"` for Gemini), forcing the provider API to return valid JSON. If JSON parsing still fails, catch the error and feed it back to the LLM (auto-retry loop up to 3 times) to let it self-correct.

### C. Fix for Persistent Git Branch Cache Inheritance
- **Recommendation**: During initialization or starting a new plan, if the integration branch exists, check it out and force-reset it to the base branch (`git reset --hard base_branch`). Update `noctifab clean` to prune all local task branches (`noctifab/task-*`) and feature branches (`noctifab/feature-*`).

---

## 5. Roadmap to Level 4 Autonomy (The self-healing Dark Factory)

To ensure `noctifab` never stalls or crashes and operates completely unattended (Level 4), we recommend introducing **meta-loops** around the core orchestrator:

### 1. The Re-Planning Meta-Loop (Self-Healing DAG)
- **Concept**: Eliminate hard stops when a task reaches its max retry limit.
- **Mechanism**: If a task fails validation repeatedly, spawn a **Diagnose Agent** to analyze the logs and codebase. The agent dynamically alters the DAG by:
  - Inserting a preparing task (e.g., refactoring or package install) ahead of the failed task.
  - Correcting test definitions if the test writer wrote an invalid assertion.
  - Resetting the task retry counter to continue.

### 2. Dynamic Sandbox Self-Provisioning
- **Concept**: Prevent stalls from missing dependencies or databases on the host system.
- **Mechanism**: Parse stderr for environment issues (e.g., `ConnectionRefusedError`, `ModuleNotFoundError`) and trigger auto-setup scripts (e.g., `docker compose up -d` or `pip install`) inside the sandbox.

### 3. Auto-Conflict Resolution (Self-Healing Rebase)
- **Concept**: Prevent merge blockages when applying task commits.
- **Mechanism**: If a git merge/rebase conflict occurs, capture the conflict diff and spawn a **Conflict Resolution Agent** to surgically resolve conflicts, commit, and resume.

---

## 6. Adoption Assessment: Can a user leverage Noctifab today?

### Verdict: **Not for production use without close human supervision (Level 2/3 Gated).**

- **Capability**: Noctifab is highly capable of decomposing requirements and implementing correct logic for self-contained, greenfield tasks. The backoff logic, test structure, and mock setups generated were mathematically and structurally correct.
- **Limitations**: The tool is highly prone to silent regressions, branch misalignment, and state drift. Because it can report success while deleting half of the codebase (due to configuration issues), a developer must verify every run.
- **Recommendations**: Developers can leverage `noctifab` as an **interactive assistant (Level 2)** to write scaffolds and initial tests on dedicated task branches, but automatic merges and PR finalizations should remain disabled until branch drift protection and structured outputs are fully implemented.
