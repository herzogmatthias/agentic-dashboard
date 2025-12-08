# Tasks: Testing Agent Implementation

## Relevant Files

- `src/models/testing_agent.py` - Pydantic models for TestAgentInput, TestAgentResult, and TestReport
- `src/models/testing_agent.test.py` - Unit tests for testing agent models
- `src/models/backend_dev.py` - Updated DevReport model with current_state/changes structure
- `src/tools/backend_dev/testing.py` - Testing-specific tools (run_npm_test, read_dev_report)
- `src/tools/backend_dev/testing.test.py` - Unit tests for testing tools
- `src/tools/backend_dev/__init__.py` - Updated exports to include testing tools
- `src/agents/backend_dev_team/tester/agent.py` - Main Testing Agent implementation
- `src/agents/backend_dev_team/tester/prompts.py` - Testing Agent system prompts
- `src/agents/backend_dev_team/tester/__init__.py` - Package exports
- `src/agents/backend_dev_team/loop/agent.py` - Updated loop agent with proper Tester integration
- `src/agents/backend_dev_team/loop/tools.py` - State keys and helpers for testing state
- `src/agents/backend_dev_team/loop/escalation.py` - Human escalation handling logic
- `tests/agents/test_testing_agent.py` - Integration tests for Testing Agent
- `tests/tools/test_testing_tools.py` - Unit tests for testing tools

### Notes

- Unit tests should typically be placed alongside the code files they are testing.
- Use `pytest` to run Python tests.
- The Testing Agent operates within the Google ADK framework.
- All Pydantic models should be defined in the `src/models/` directory.
- The Testing Agent replaces the current placeholder `TesterResult` in the loop agent.
- Test files in the sample-dashboard project use Jest (TypeScript): `tests/api/` for routes, `tests/lib/` for helpers.
- Maximum 5 total retries across the Dev→Test→QA loop per artifact.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:

- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 1.0 Define Pydantic models for Testing Agent contracts

  - [x] 1.1 Create `src/models/testing_agent.py` with `TestReport` model containing: `artifact_id`, `timestamp`, `current_tests`, `test_files_created`, `test_files_modified`, `test_files_deleted`, `tests_run`, `tests_failed`, `failed_test_names`, `command_used`, `output_snippet`, `notes`
  - [x] 1.2 Add `TestAgentInput` model with: `run_id`, `artifact`, `workspace_root`, `dev_report_path`, `backend_manifest_path`, `test_report_dir`, `previous_test_summary`, `previous_qa_summary`
  - [x] 1.3 Add `TestAgentResult` model with: `run_id`, `artifact_id`, `status` (Literal["success", "failed", "partial"]), `summary`, `test_report`, `needs_dev_fix`, `needs_spec_clarification`, `error_details`
  - [x] 1.4 Add model to `src/models/__init__.py` exports
  - [x] 1.5 Write unit tests for model validation in `tests/models/test_testing_agent.py`

- [x] 2.0 Implement Testing Agent tools

  - [x] 2.1 Create `src/tools/backend_dev/tester/__init__.py` with tool implementations
  - [x] 2.2 Implement `run_npm_test(pattern: Optional[str])` tool that executes Jest tests and returns `exit_code`, `stdout`, `stderr`
  - [x] 2.3 Implement `read_dev_report(path: str)` tool that reads and parses DevReport JSON
  - [x] 2.4 Implement `get_test_sample_rows(table: str, limit: int = 1)` tool with hard limit of 1 row for fixture generation
  - [x] 2.5 Add `delete_file(path: str)` tool to tester tools (for test file cleanup)
  - [x] 2.6 Create `get_tester_tools()` factory function that returns all tester tools
  - [x] 2.7 Update `src/tools/backend_dev/__init__.py` to export tester tools
  - [x] 2.8 Write unit tests for tools in `tests/tools/test_tester_tools.py`

- [ ] 3.0 Implement the Testing Agent core logic

  - [ ] 3.1 Create `src/agents/backend_dev_team/tester/prompts.py` with `build_tester_prompt()` function
  - [ ] 3.2 Write route testing instructions in prompt (happy path, contract tests, HTTP assertions)
  - [ ] 3.3 Write helper testing instructions in prompt (unit tests, edge cases, invariants)
  - [ ] 3.4 Create `src/agents/backend_dev_team/tester/agent.py` with `create_tester_agent()` factory
  - [ ] 3.5 Implement dynamic instruction provider `tester_instruction_provider(context)` that reads state
  - [ ] 3.6 Configure agent with `LiteLlm`, `PlanReActPlanner`, tools from `get_tester_tools()`, and `output_schema=TestAgentResult`
  - [ ] 3.7 Add state key constants for tester state (dev_report_path, previous_test_summary, etc.)
  - [ ] 3.8 Update `src/agents/backend_dev_team/tester/__init__.py` with exports

- [ ] 4.0 Integrate Testing Agent into the artifact loop

  - [ ] 4.1 Update `src/agents/backend_dev_team/loop/tools.py` with new state keys: `STATE_KEY_DEV_REPORT_PATH`, `STATE_KEY_TEST_REPORT_PATH`, `STATE_KEY_RETRY_COUNT`
  - [ ] 4.2 Replace placeholder `create_tester_agent()` in `loop/agent.py` with import from `tester/agent.py`
  - [ ] 4.3 Update `_check_tester_success()` to check `TestAgentResult.status` instead of `TesterResult`
  - [ ] 4.4 Add logic to persist `TestReport` to `artifacts/qa/tests/<artifact_id>.test_report.json` after each iteration
  - [ ] 4.5 Implement retry counting: increment `STATE_KEY_RETRY_COUNT` on each Dev/Test/QA failure
  - [ ] 4.6 Add routing logic for `needs_dev_fix` → back to Dev, `needs_spec_clarification` → escalate to Planner
  - [ ] 4.7 Update `BackendDevLoopAgent._run_async_impl()` to pass `dev_report_path` and `previous_test_summary` to Tester state

- [ ] 5.0 Update DevReport model with new fields

  - [ ] 5.1 Create `DevCurrentState` model with: `code_path`, `dependent_code_paths`, `exports` (optional)
  - [ ] 5.2 Create `DevChanges` model with: `files_created`, `files_modified`, `files_deleted`, `dependent_code_paths_added`, `dependent_code_paths_removed`
  - [ ] 5.3 Update `DevReport` model to include `current_state: DevCurrentState` and `changes: DevChanges`
  - [ ] 5.4 Add `action_summary`, `implementation_notes`, `next_steps` fields to DevReport
  - [ ] 5.5 Update Backend Dev Agent prompt to populate new DevReport fields
  - [ ] 5.6 Ensure backward compatibility with existing DevReport usages

- [ ] 6.0 Implement escalation handling in orchestrator

  - [ ] 6.1 Create `src/agents/backend_dev_team/loop/escalation.py` with escalation logic
  - [ ] 6.2 Define `EscalationReason` enum: `MAX_RETRIES`, `SPEC_CLARIFICATION`, `COMPLEXITY`, `UNKNOWN_ERROR`
  - [ ] 6.3 Implement `check_should_escalate(retry_count, result)` function that returns `(should_escalate, reason)`
  - [ ] 6.4 Implement `create_escalation_prompt(artifact, reason, context)` that builds human-readable prompt
  - [ ] 6.5 Update `BackendDevLoopAgent._run_async_impl()` to call escalation check when retry_count >= 5
  - [ ] 6.6 Add `STATE_KEY_ESCALATION_PENDING` and `STATE_KEY_ESCALATION_REASON` state keys
  - [ ] 6.7 Implement `handle_escalation_response(response)` to process user decision (retry/skip/abort)
  - [ ] 6.8 Emit escalation event that orchestrator can catch to pause and prompt user

- [ ] 7.0 Write tests for Testing Agent components
  - [ ] 7.1 Create `tests/agents/test_testing_agent.py` with integration tests
  - [ ] 7.2 Write test for route artifact flow: artifact → Tester → TestReport with test files
  - [ ] 7.3 Write test for helper artifact flow: artifact → Tester → TestReport (no QA)
  - [ ] 7.4 Write test for `needs_dev_fix=True` routing back to Dev
  - [ ] 7.5 Write test for `needs_spec_clarification=True` escalation
  - [ ] 7.6 Write test for retry limit (5 retries → escalation)
  - [ ] 7.7 Write test for TestReport persistence to disk
  - [ ] 7.8 Create `tests/tools/test_testing_tools.py` with unit tests for `run_npm_test`, `read_dev_report`
