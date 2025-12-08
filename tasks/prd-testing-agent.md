# PRD: Testing Agent

## 1. Introduction/Overview

The **Testing Agent** is a specialized agent within the multi-agent dashboard-generation pipeline responsible for verifying backend implementations at the code level via automated tests. It operates after the Backend Dev Agent produces code and before the Data QA Agent validates data correctness.

The Testing Agent receives a conceptual artifact specification (from Planner) along with the Dev implementation context, then writes/updates automated tests, executes them, and emits a structured **Test Report**. This report feeds into the artifact loop's retry logic and is later consumed by a deterministic manifest builder.

**Problem Solved:** Currently, there is no automated verification step between code implementation and data validation. The Testing Agent fills this gap by ensuring each backend artifact (route or helper) has adequate test coverage before proceeding to QA.

---

## 2. Goals

1. **Automated Test Generation:** Generate or update test files for each backend artifact based on the DevReport and artifact specification.
2. **Test Execution:** Run relevant tests and capture structured results (pass/fail counts, output snippets).
3. **Structured Reporting:** Emit a TestReport per artifact per iteration that enables retry decisions and manifest building.
4. **Loop Integration:** Provide clear signals (`needs_dev_fix`, `needs_spec_clarification`) to drive the Dev→Test→QA loop.
5. **Human Escalation:** Support escalation to the orchestrator when retries are exhausted, prompting the user for a decision.

---

## 3. User Stories

1. **As the Orchestrator**, I want to invoke the Testing Agent with a DevReport and artifact spec so that I can verify the implementation before passing it to QA.

2. **As the Artifact Loop**, I want to receive a TestAgentResult with clear status (`success`, `failed`, `partial`) and flags (`needs_dev_fix`, `needs_spec_clarification`) so that I can decide whether to retry Dev, escalate to Planner, or proceed to QA.

3. **As the Manifest Builder**, I want to read TestReports from disk so that I can populate `test_paths` and test status in the BackendManifest without invoking any LLM.

4. **As a Developer debugging the pipeline**, I want to see which tests failed and why (via `failed_test_names` and `output_snippet`) so that I can understand what went wrong.

5. **As the Orchestrator**, when 5 total retries are exhausted for an artifact, I want the Testing Agent to escalate so that I can pause and prompt the user for a decision on how to proceed.

---

## 4. Functional Requirements

### 4.1 Input Contract (TestAgentInput)

1. The Testing Agent **must** accept a `TestAgentInput` Pydantic model containing:
   - `run_id` (str): Current pipeline run ID for tracing.
   - `artifact` (PlannerArtifactTodo): Conceptual description of the artifact.
   - `workspace_root` (str): Filesystem root of the backend project.
   - `dev_report_path` (str): Path to the latest DevReport JSON for this artifact.
   - `backend_manifest_path` (Optional[str]): Read-only path to a previously built manifest.
   - `test_report_dir` (str, default `"artifacts/qa/tests"`): Directory for TestReports.
   - `previous_test_summary` (Optional[str]): Summary from last Test run (for fix iterations).
   - `previous_qa_summary` (Optional[str]): Summary from last QA run.

### 4.2 Output Contract (TestAgentResult & TestReport)

2. The Testing Agent **must** return a `TestAgentResult` Pydantic model containing:

   - `run_id` (str): Echo of input run ID.
   - `artifact_id` (str): ID of the artifact.
   - `status` (Literal["success", "failed", "partial"]): Overall outcome.
   - `summary` (str): Human-readable explanation.
   - `test_report` (TestReport): Full structured report.
   - `needs_dev_fix` (bool): True if failures indicate implementation bugs.
   - `needs_spec_clarification` (bool): True if failures indicate unclear specs.
   - `error_details` (Optional[str]): Technical details if tests couldn't execute.

3. The `TestReport` model **must** contain:
   - `artifact_id` (str): Which artifact this report refers to.
   - `timestamp` (str): ISO timestamp of this iteration.
   - `current_tests` (List[str]): All test file paths currently covering this artifact.
   - `test_files_created` (List[str]): Test files created this iteration.
   - `test_files_modified` (List[str]): Test files modified this iteration.
   - `test_files_deleted` (List[str]): Test files removed this iteration.
   - `tests_run` (int): Number of tests executed.
   - `tests_failed` (int): Number of failing tests.
   - `failed_test_names` (List[str]): Identifiers of failing tests.
   - `command_used` (str): Test command executed (e.g., `npm test -- <pattern>`).
   - `output_snippet` (Optional[str]): Trimmed stdout/stderr for debugging.
   - `notes` (Optional[str]): Additional notes, limitations, or TODOs.

### 4.3 Tools

4. The Testing Agent **must** have access to the following filesystem tools:

   - `read_file(path)`: Inspect existing test files and code.
   - `write_file(path, content)`: Create new test files.
   - `edit_file(path, diff_or_patch)`: Modify existing tests.
   - `delete_file(path)`: Remove test files during refactoring.
   - `file_exists(path)`: Check if tests already exist.
   - `list_directory(path)`: Explore test directories.

5. The Testing Agent **must** have access to test execution tools:

   - `run_npm_test(pattern: Optional[str])`: Run tests globally or filtered by pattern. Returns `exit_code`, `stdout`, `stderr`.

6. The Testing Agent **must** have access to context tools:
   - `read_dev_report(path)`: Read DevReport JSON to extract code paths and implementation notes.
   - `get_sample_rows_tool`: Limited access (first row only) for generating realistic test fixtures. **Not for data correctness validation.**

### 4.4 Workflow: Testing Routes

7. For `artifact.kind == "route"`, the Testing Agent **must**:
   - Read the DevReport to get `http_path`, `http_method`, `query_params`, `canonical_query`, `code_path`.
   - Create or update test file at `tests/api/<artifact_id>.test.ts`.
   - Generate at minimum:
     - One "happy path" test using `canonical_query`.
     - Basic contract tests (missing required param → 400, invalid enum → 400).
   - Assert HTTP status, JSON response, and structural match to `expected_shape`.
   - Run tests via `run_npm_test(pattern=...)`.
   - Populate TestReport with results.

### 4.5 Workflow: Testing Helpers

8. For `artifact.kind == "helper"`, the Testing Agent **must**:
   - Read the DevReport to get `code_path`, `exports`, and dependencies.
   - Create or update test file at `tests/lib/<helper_name>.test.ts`.
   - Generate unit tests focusing on:
     - Pure function behavior.
     - Clear invariants.
     - Edge cases (empty input, invalid args).
   - Run tests via `run_npm_test(pattern=...)`.
   - Populate TestReport with results.

### 4.6 Test Generation Approach

9. The Testing Agent **must** generate tests from scratch using the LLM based on DevReport context. No predefined templates are used.

### 4.7 Retry & Escalation Logic

10. The artifact loop **must** track total retries across the entire Dev→Test→QA loop per artifact.

11. After **5 total retries** for an artifact, the Testing Agent **must** signal escalation by:

    - Setting `status = "failed"`.
    - Including escalation context in `error_details`.
    - The orchestrator will then pause and prompt the user via CLI/API for a decision.

12. On `status = "failed"` with `needs_dev_fix = True`:

    - Artifact state transitions to `DEV_IN_PROGRESS` for another Dev iteration.

13. On `status = "failed"` with `needs_spec_clarification = True`:

    - Artifact state transitions to `PLANNED/NEEDS_REPLAN` for Planner adjustment.

14. On `status = "success"`:

    - If `artifact.kind == "route"`: state → `WAITING_FOR_QA`.
    - If `artifact.kind == "helper"`: state → `COMPLETED`.

15. On `status = "partial"`:
    - Treat as soft failure; iterate with Dev/Test or proceed to QA with warning (configurable).

### 4.8 Report Persistence

16. The orchestrator **must** persist TestReports to disk at:

    - `artifacts/qa/tests/<artifact_id>.test_report.json` (latest version).
    - Optionally archive older iterations.

17. The manifest builder **must** read TestReports from `artifacts/qa/tests/*.test_report.json` to populate `test_paths` in the BackendManifest.

---

## 5. Non-Goals (Out of Scope)

1. **Data Correctness Validation:** The Testing Agent does not validate that backend outputs match the dataset. That is the Data QA Agent's responsibility.

2. **Business Logic Implementation:** The Testing Agent does not write or fix endpoint code. That is the Backend Dev Agent's responsibility.

3. **Artifact Ordering:** The Testing Agent does not decide which artifact to process next. That is the Planner/Orchestrator's responsibility.

4. **Manifest Writing:** The Testing Agent does not write the BackendManifest directly. It only emits TestReports for the manifest builder to consume.

5. **Full Dataset Access:** The Testing Agent has only limited access to sample data (first row) for fixture generation, not full dataset queries.

---

## 6. Design Considerations

### File Structure

```
artifacts/
├── backend/
│   └── dev/
│       └── <artifact_id>.dev_report.json
└── qa/
    └── tests/
        └── <artifact_id>.test_report.json

tests/
├── api/
│   └── <artifact_id>.test.ts      # Route tests
└── lib/
    └── <helper_name>.test.ts      # Helper tests
```

### Test File Conventions

- Route tests: `tests/api/<artifact_id>.test.ts`
- Helper tests: `tests/lib/<helper_name>.test.ts`
- Use descriptive test names that map to `failed_test_names` in reports.

### TestReport Example (Route)

```json
{
  "artifact_id": "route_attrition_by_income",
  "timestamp": "2025-01-01T12:30:00Z",
  "current_tests": ["tests/api/route_attrition_by_income.test.ts"],
  "test_files_created": ["tests/api/route_attrition_by_income.test.ts"],
  "test_files_modified": [],
  "test_files_deleted": [],
  "tests_run": 4,
  "tests_failed": 0,
  "failed_test_names": [],
  "command_used": "npm test -- route_attrition_by_income.test.ts",
  "output_snippet": "Test Suites: 1 passed, 1 total\nTests: 4 passed, 4 total\n",
  "notes": "Covers happy path, missing required param, and invalid enum value."
}
```

---

## 7. Technical Considerations

### Tech Stack

- **Runtime:** Next.js/TypeScript (Node.js)
- **Test Framework:** Jest (via `npm test`)
- **Agent Framework:** Google ADK
- **Models:** Pydantic for input/output contracts

### Dependencies

- Requires Backend Dev Agent to have completed and emitted a DevReport.
- Requires access to the workspace filesystem (Daytona sandbox).
- Integrates with the artifact loop state machine in the orchestrator.

### DevReport Updates

The DevReport emitted by Backend Dev Agent should include:

```python
class DevReport(BaseModel):
    artifact_id: str
    timestamp: str
    action_summary: str

    # Current state (for manifest builder)
    current_state: DevCurrentState  # code_path, dependent_code_paths, exports

    # Delta for this iteration
    changes: DevChanges  # files_created, files_modified, files_deleted, deps added/removed

    implementation_notes: str
    next_steps: str
```

### Escalation Flow

When retries exhausted:

1. Testing Agent returns `status="failed"` with escalation context.
2. Orchestrator receives the result and detects retry limit reached.
3. Orchestrator pauses the pipeline and prompts user via CLI/API.
4. User decides: retry with guidance, skip artifact, or abort run.
5. Orchestrator resumes based on user decision.

---

## 8. Success Metrics

1. **Test Coverage:** ≥90% of artifacts have at least one passing test before reaching QA.
2. **Loop Efficiency:** Average iterations per artifact ≤ 2 (most pass on first or second try).
3. **Escalation Rate:** <10% of artifacts require human escalation.
4. **False Positives:** <5% of `needs_dev_fix` signals are incorrect (test bug, not impl bug).
5. **Report Completeness:** 100% of TestReports contain valid `current_tests` for manifest building.

---

## 9. Open Questions

1. **Test Framework Flexibility:** Should we support other test frameworks (e.g., Vitest) in the future? If so, how should `command_used` be parameterized?

2. **Parallel Testing:** Can multiple artifacts' tests run in parallel, or must they be sequential to avoid conflicts?

3. **Test Isolation:** How do we ensure route tests don't interfere with each other (e.g., shared database state)?

4. **Coverage Reporting:** Should TestReport include code coverage metrics (e.g., from Istanbul/nyc)?

5. **Snapshot Testing:** Should the Testing Agent use Jest snapshots for response shape validation?

---

## Appendix: State Machine Reference

```
PLANNED
    ↓
DEV_IN_PROGRESS
    ↓ (DevReport emitted)
WAITING_FOR_TEST
    ↓
TEST_IN_PROGRESS
    ↓ (TestReport emitted)
    ├─→ [success, helper] → COMPLETED
    ├─→ [success, route] → WAITING_FOR_QA → QA_IN_PROGRESS → COMPLETED
    ├─→ [failed, needs_dev_fix] → DEV_IN_PROGRESS (retry)
    ├─→ [failed, needs_spec_clarification] → PLANNED (replan)
    └─→ [failed, retries exhausted] → ESCALATE → (user decision)
```

**Total retry budget per artifact: 5** (across all Dev→Test→QA iterations)
