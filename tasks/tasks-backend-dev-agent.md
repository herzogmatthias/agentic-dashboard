# Tasks: Backend Dev Agent

## Relevant Files

- `src/agents/backend_dev_team/dev/__init__.py` - Package exports for Backend Dev Agent
- `src/agents/backend_dev_team/dev/prompts.py` - System prompt for single-artifact workflow
- `src/agents/backend_dev_team/dev/callbacks.py` - State injection and context callbacks
- `src/agents/backend_dev_team/dev/agent.py` - Main Backend Dev Agent definition
- `src/models/backend_dev.py` - I/O schemas (BackendDevInput, BackendDevResult, DevReport, FileChange)
- `src/tools/backend_dev/` - Backend Dev specific tools (create_helper_tool)
- `src/tools/shared/` - Shared tools that can be reused across agents
- `src/agents/backend_dev_team/loop/agent.py` - Loop Agent (update create_dev_agent factory)
- `src/agents/backend/tools.py` - Existing tools to reuse (create_api, create_model, etc.)
- `src/agents/backend/prompts.py` - Reference for prompt adaptation
- `tests/agents/test_backend_dev_agent.py` - Unit tests for Backend Dev Agent

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `agent.py` and `test_agent.py` in the same directory or `tests/` folder).
- Use `pytest [optional/path/to/test/file]` to run tests.
- Reuse tools from `src/agents/backend/` where possible to minimize duplication.
- Models follow existing pattern in `src/models/` (e.g., `backend_manifest.py`, `data_profile.py`)
- `BackendDevResult` with nested `DevReport` is the agent's structured output (not a tool)

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:

- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 1.0 Create folder structure for Backend Dev Agent

  - [x] 1.1 Create `src/agents/backend_dev_team/dev/` directory
  - [x] 1.2 Create `__init__.py` with placeholder exports

- [x] 2.0 Define I/O schemas (BackendDevInput, BackendDevResult, DevReport)

  - [x] 2.1 Create `src/models/backend_dev.py`
  - [x] 2.2 Import `PlannerArtifactTodo` from `src/models/backend_planner_todos.py`
  - [x] 2.3 Define `FileChange` model with `path`, `action` (created/modified), `description`
  - [x] 2.4 Define `DevReport` model with artifact_id, artifact_type, status, summary, files_changed, dependencies, lint_passed, type_check_passed, errors, timestamp
  - [x] 2.5 Define `BackendDevInput` model with run_id, artifact, workspace_root, previous_summaries
  - [x] 2.6 Define `BackendDevResult` model with status, summary, report (DevReport) - this is the agent's structured output
  - [x] 2.7 Export schemas from `src/models/__init__.py`

- [x] 3.0 Implement tools for Backend Dev Agent

  - [x] 3.1 Create `src/tools/backend_dev/__init__.py` directory and init file
  - [x] 3.2 Implement `create_helper_tool(name, content)` - creates TypeScript helper at `src/lib/{name}.ts` with syntax validation
  - [x] 3.3 Evaluate which existing tools from `src/agents/backend/tools.py` should move to `src/tools/shared/` (get_sample_rows, inspect_json_preview, create_api, create_model, search_content, run_lint, run_type_check)
  - [x] 3.4 Create `get_dev_tools()` function that returns list of all tools for the agent
  - [x] 3.5 Ensure MCP filesystem toolset is included via `create_filesystem_toolset()`

- [x] 4.0 Build system prompt for single-artifact workflow

  - [x] 4.1 Create `src/agents/backend_dev_team/dev/prompts.py`
  - [x] 4.2 Adapt base structure from `src/agents/backend/prompts.py`
  - [x] 4.3 Update role description to emphasize single-artifact focus ("You receive ONE artifact to implement")
  - [x] 4.4 Document injected context: artifact details, dashboard concept, data profile, previous_summaries
  - [x] 4.5 Keep TypeScript rules section (no `any`, explicit types, proper generics)
  - [x] 4.6 Update tool documentation to include `create_helper_tool`
  - [x] 4.7 Remove `write_backend_manifest_tool` references
  - [x] 4.8 Define workflow steps: understand artifact → check existing code → create files → validate → return structured DevReport
  - [x] 4.9 Add output requirement: "Your final response MUST conform to BackendDevResult schema with a complete DevReport"

- [x] 5.0 Create Backend Dev Agent definition

  - [x] 5.1 Create `src/agents/backend_dev_team/dev/agent.py`
  - [x] 5.2 Import LlmAgent, PlanReActPlanner from google.adk
  - [x] 5.3 Import `BackendDevResult` from `src/models/backend_dev`
  - [x] 5.4 Import tools from `src/tools/backend_dev/` and shared tools
  - [x] 5.5 Create `backend_dev_instruction_provider()` function that injects workspace_root, artifact, and metrics_ref_context
  - [x] 5.6 Enhanced `inject_artifact_context_for_dev` in `loop/callbacks.py` to handle all Dev Agent state init (run_dir, workspace_root, metrics_ref lookup, cleaned_data_files). No separate callbacks.py needed for Dev Agent since it only runs within Loop Agent.
  - [x] 5.7 Define `backend_dev_agent` LlmAgent with model `xai/grok-code-fast-1`, PlanReActPlanner, tools, output_schema=BackendDevResult
  - [x] 5.8 Create `create_backend_dev_agent(workspace_root)` factory function for Loop Agent to use
  - [x] 5.9 Export agent and factory from `__init__.py`

- [x] 6.0 Integrate with Loop Agent

  - [x] 6.1 Import `create_backend_dev_agent` in `src/agents/backend_dev_team/loop/agent.py`
  - [x] 6.2 Update `create_dev_agent()` factory to use the new Backend Dev Agent
  - [x] 6.3 Loop Agent uses state for artifact (via `inject_artifact_context_for_dev` callback) - no explicit `BackendDevInput` passing needed
  - [x] 6.4 Update Loop Agent to extract `DevReport` from `BackendDevResult` and store summary in `previous_summaries` for next artifact (`_append_dev_summary_to_state`)
  - [x] 6.5 Updated `_check_dev_success` to handle both old `DevResult` and new `BackendDevResult` formats

- [x] 7.0 Unit tests
  - [x] 7.1 Create `tests/agents/test_backend_dev_agent.py`
  - [x] 7.2 Test `FileChange` schema validation
  - [x] 7.3 Test `DevReport` schema validation with all fields
  - [x] 7.4 Test `BackendDevInput` schema validation
  - [x] 7.5 Test `BackendDevResult` schema validation
  - [x] 7.6 Test `create_helper_tool` creates file at correct path
  - [x] 7.7 Test `create_backend_dev_agent` factory returns properly configured agent
