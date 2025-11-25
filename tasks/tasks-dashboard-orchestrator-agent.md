## Relevant Files

- `agentic-dashboard/src/agent.py` - Exposes the ADK `root_agent`; will be updated to use the new orchestrator agent.
- `agentic-dashboard/src/agents/orchestrator/agent.py` - New orchestrator agent coordinating data analysis and planner agents.
- `agentic-dashboard/src/agents/data_analysis/agent.py` - Existing Data Analysis Agent; will be updated to use new tools and artifact conventions.
- `agentic-dashboard/src/agents/planner/agent.py` - Planner agent; will be updated to consume the new handoff message and produce structured output.
- `agentic-dashboard/src/models/data_analysis_agent_output.py` - Structured output for the Data Analysis Agent; may be extended if needed.
- `agentic-dashboard/src/models/planner_output.py` - New Pydantic model representing the planner’s structured output.
- `agentic-dashboard/src/prompts/system_prompts.py` - System prompts for agents; will include orchestrator and planner prompt updates.
- `agentic-dashboard/src/prompts/user_prompts.py` - User-facing prompt builders (e.g., planner handoff) to be aligned with the new orchestrator design.
- `agentic-dashboard/src/tools/filesystem.py` - Filesystem tools; may be extended for sandbox-to-local mapping and metrics summary writing.
- `agentic-dashboard/src/tools/planner.py` - Planner tools (e.g., `create_dashboard_tool`) that persist dashboard specs.
- `agentic-dashboard/src/core/daytona_client.py` - Daytona sandbox client; relevant for copying artifacts from sandbox to local.
- `agentic-dashboard/src/app/main.py` - Entry point for the existing app/CLI; may be wired to call the orchestrator.
- `agentic-dashboard/tests/agents/test_orchestrator_agent.py` - New tests for orchestrator behavior and flow.
- `agentic-dashboard/tests/agents/test_planner_integration.py` - New tests covering planner integration and structured output.

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `MyComponent.py` and `test_my_component.py` in the same directory) or under a `tests/` package following existing project conventions.
- Use `pytest` or the project’s configured test runner (if specified in the repo) to run tests. If no test tooling is configured, add minimal, focused tests and document how to run them.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:

- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 0.0 Create feature branch

  - [x] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/dashboard-orchestrator-agent`)

- [x] 1.0 Define orchestrator architecture and ADK multi-agent setup

  - [x] 1.1 Review `tasks/prd-dashboard-orchestrator-agent.md` and highlight key flows (user → data_analysis → planner → summary).
  - [x] 1.2 Review Google ADK multi-agent documentation, focusing on `LlmAgent`, `SequentialAgent`, and sub-agent hierarchies.
  - [x] 1.3 Decide on the orchestrator implementation pattern (single `LlmAgent` with tools vs. `SequentialAgent` pipeline) and document the choice in the code (docstring or comment).
  - [x] 1.4 Design the agent tree and shared state keys (e.g., `run_dir`, `data_analysis_output`, `planner_output`) to be used across orchestrator, Data Analysis Agent, and Planner.
  - [x] 1.5 Create `agentic-dashboard/src/agents/orchestrator/agent.py` with a stub orchestrator agent that can be instantiated but does not yet call sub-agents.
  - [x] 1.6 Update `agentic-dashboard/src/agent.py` so `root_agent` points to the new orchestrator agent (while keeping the old data analysis entry available if useful for debugging).

- [x] 2.0 Implement orchestrator prompts, message routing, and per-agent conversation histories

  - [x] 2.1 Define or update system prompts for the orchestrator in `src/prompts/system_prompts.py` to clearly describe its role as coordinator and mediator.
  - [x] 2.2 Implement the orchestrator's initial interaction logic to collect goal description, audience, primary use case, and constraints from the user.
  - [x] 2.3 Implement logic to confirm that the user has uploaded valid data (e.g., dataset path), and block progression until this requirement is met.
  - [x] 2.4 Implement message routing so that:
    - User-facing questions and summaries are surfaced only to the user.
    - Agent-facing instructions (for Data Analysis Agent and Planner) are constructed by the orchestrator and sent only to the relevant sub-agent.
  - [x] 2.5 Ensure each agent (orchestrator, Data Analysis Agent, Planner) retains its own conversation history, using ADK's session/branching mechanisms to avoid mixing transcripts.
  - [x] 2.6 When delegating to sub-agents, implement the orchestrator as the effective "user" of those agents, sending concise, context-rich prompts instead of the full orchestrator history.

- [ ] 3.0 Implement artifact management, metrics summary tooling, and sandbox-to-local path mapping

  - [ ] 3.1 Review current artifact copying logic in `src/agents/data_analysis/agent.py` and `src/core/daytona_client.py` to understand how files move from sandbox to local.
  - [ ] 3.2 Implement a path-mapping utility (in `src/tools/filesystem.py` or similar) that maps sandbox-relative paths in `additional_artifacts_path` to local run-directory paths.
  - [ ] 3.3 Define and document conventions for “important” artifacts:
    - Required: `data_profile.md`, `cleaning_summary.md`.
    - Optional: additional metrics/summary artifacts under a well-defined folder (e.g., `artifacts/data_analysis/important/` or inside the `cleaned` folder).
  - [ ] 3.4 Implement a new filesystem/tool function that the Data Analysis Agent can use to write a summarized metrics artifact (e.g., `write_metrics_summary_tool`) in the agreed location.
  - [ ] 3.5 Update the Data Analysis Agent to use the new metrics summary tool when it computes additional metrics, ensuring metrics not present in `cleaned.csv` are also written under the `cleaned` (or equivalent) folder.
  - [ ] 3.6 Adjust `copy_data_analysis_artifacts_after_agent` (or equivalent post-callback) so that it copies required and important artifacts into the local run directory and updates `additional_artifacts_path` with local-relative paths.
  - [ ] 3.7 Ensure planner-related tools that currently assume remote/sandbox paths can accept local paths, reusing Data Analysis tools where appropriate with small adjustments.

- [ ] 4.0 Implement planner integration, structured outputs, and dashboard spec persistence

  - [ ] 4.1 Design and create a `PlannerOutput` Pydantic model in `src/models/planner_output.py` that matches the PRD schema (`dashboard_spec_path`, `needs_additional_analysis`, `needs_user_clarification`, `meta`).
  - [ ] 4.2 Update the Planner Agent (e.g., `src/agents/planner/agent.py`) to produce structured output conforming to `PlannerOutput`, ensuring it always returns a valid JSON payload.
  - [ ] 4.3 Implement the orchestrator’s logic to construct the Planner handoff message:
    - Include goal, audience, primary use case, and constraints.
    - Include paths to `data_profile.md` and `cleaning_summary.md`.
    - Include paths or a JSON summary for relevant additional artifacts/metrics.
  - [ ] 4.4 Integrate `create_dashboard_tool` (in `src/tools/planner.py`) or similar to persist the dashboard spec JSON under the current run directory and capture the resulting `dashboard_spec_path`.
  - [ ] 4.5 Implement orchestrator handling of `needs_additional_analysis`:
    - For v1, decide whether to re-invoke the Data Analysis Agent or expose these as “next steps” to the user, and implement that behavior.
  - [ ] 4.6 Implement orchestrator handling of `needs_user_clarification`:
    - Surface questions to the user, collect answers, and either re-invoke the Planner or present unresolved questions in the final summary (per the chosen v1 strategy).
  - [ ] 4.7 Implement the final user-facing summary that combines planner `meta`, key insights from data profiling/cleaning, and any next steps or open questions.

- [ ] 5.0 Implement execution limits, timeouts, retries, and error surfacing

  - [ ] 5.1 Configure a maximum number of tool/function calls per agent (target ~15) using the mechanisms provided by Google ADK or wrapper logic in the orchestrator.
  - [ ] 5.2 Implement timeouts (5–10 minutes) for critical agent invocations (data analysis, planner) and ensure long-running operations are cancelled or marked as timed out.
  - [ ] 5.3 Implement retry logic with at most 2 retries for recoverable failures (e.g., transient I/O issues) and make the retry conditions explicit in the code.
  - [ ] 5.4 Ensure that, after exhausting retries or on non-recoverable errors, the orchestrator surfaces clear, user-friendly error messages that describe what failed and suggest next steps.
  - [ ] 5.5 Add logging and/or tracing around timeouts and retries so that failures can be debugged from logs or Phoenix traces.

- [ ] 6.0 Add tests, tracing, and wire orchestrator as the root agent in the ADK chat UI
  - [ ] 6.1 Add unit tests for the orchestrator’s control flow, mocking the Data Analysis Agent and Planner Agent to verify correct routing and state updates.
  - [ ] 6.2 Add tests for the path-mapping utility and metrics summary tool to ensure correct handling of sandbox vs. local paths and artifact locations.
  - [ ] 6.3 Add tests for the Planner integration, verifying that `PlannerOutput` is correctly produced and parsed, and that `dashboard_spec_path` points to an existing file.
  - [ ] 6.4 Verify that Phoenix tracing (or equivalent) is correctly capturing orchestrator, data analysis, and planner events for end-to-end runs.
  - [ ] 6.5 Ensure `src/agent.py` exposes the orchestrator `root_agent` and that the Google ADK simple chat UI can be launched and used to run the full flow.
  - [ ] 6.6 Document how to run the orchestrator via the chat UI and, if applicable, via a future Flask API/Next.js UI (even if the latter is out of scope for implementation, note expected integration points).
