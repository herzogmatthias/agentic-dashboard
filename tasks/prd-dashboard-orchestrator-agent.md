# Dashboard Orchestrator Agent PRD

## 1. Introduction / Overview

This feature introduces a **Dashboard Orchestrator Agent** as the main entrypoint to the existing multi-agent system built with Google ADK. Today, there are two primary agents:

- **Data Analysis Agent**: Profiles, cleans, and exports dataset artifacts (e.g., `data_profile.md`, `cleaning_summary.md`, `cleaned.csv`), running inside a Daytona sandbox.
- **Planner Agent**: Designs a dashboard plan/specification based on the user’s goals and the available data context.

Currently, these agents are run independently and require manual orchestration by the user or surrounding application. The goal of this feature is to add a **LLM-based orchestrator agent** that:

- Acts as the **single, programmatic entrypoint** (exposed via `src/agent.py` for Google ADK).
- Handles **end-to-end flow**: user goal intake, data confirmation, calling the Data Analysis Agent, and then calling the Planner Agent.
- Mediates **follow-up questions** between the Planner Agent and the user, and between the Planner Agent and the Data Analysis Agent (when additional analysis is requested).
- Returns a **structured planner output** (including a path to the dashboard spec) along with a synthesized, user-friendly explanation.

The primary users are **internal engineers** working on `agentic-dashboard` who want a clear, reusable orchestrator that can be invoked from CLI/UI without manually wiring each step.

---

## 2. Goals

1. Provide a **single root agent** (the orchestrator) that coordinates the Data Analysis Agent and Planner Agent using ADK’s multi-agent primitives.
2. Enable a **guided, conversational setup** where the orchestrator:
   - Elicits key information about the desired dashboard (goal, audience, primary use case, constraints).
   - Confirms that the user has uploaded data suitable for analysis (e.g., a CSV file).
3. Implement a **sequential orchestration flow**:
   - User interaction → Data Analysis Agent → Planner Agent → Orchestrator summary.
4. Ensure the Planner receives the **required data context**:
   - Mandatory artifacts: `data_profile.md` and `cleaning_summary.md`.
   - Optional additional artifacts and metrics derived from data analysis.
5. Define and adopt a **structured Planner output schema**, including:
   - `dashboard_spec_path` (path to a JSON spec).
   - `needs_additional_analysis` (optional list of requested analyses).
   - `needs_user_clarification` (optional list of user-facing questions).
   - `meta` object with key metadata (goal, notable segments, visual count, etc.).
6. Support **local file access** for planner-related tools, ensuring they can read artifacts created by the Data Analysis Agent even after they are copied out of the Daytona sandbox.
7. Design the orchestrator to be **extensible**, so new agents or flows can be added in the future with minimal changes.

---

## 3. User Stories

1. **As an internal engineer**, I want a single orchestrator agent I can call from `src/agent.py` so that I don’t have to manually wire separate planner and data analysis runs.
2. **As an internal engineer**, I want the orchestrator to ask the user about their dashboard goals, audience, primary use case, and constraints so the planner gets a rich, structured context.
3. **As an internal engineer**, I want the orchestrator to verify that the user has provided an input dataset (e.g., CSV) before running the Data Analysis Agent, so we avoid planner runs without data.
4. **As an internal engineer**, I want the orchestrator to automatically run the Data Analysis Agent first and wait for `success=true` before calling the Planner, so the Planner always has `data_profile` and `cleaning_summary` available.
5. **As an internal engineer**, I want the orchestrator to pass `data_profile.md`, `cleaning_summary.md`, and a curated list of additional artifacts to the Planner via an orchestrator-generated handoff message (no backwards compatibility constraints) so the Planner can reason about data quality and available features.
6. **As an internal engineer**, I want the Planner to return a structured output including a `dashboard_spec_path` and optional `needs_additional_analysis` and `needs_user_clarification` fields so the orchestrator can either finish the flow or loop back for more work.
7. **As an internal engineer**, I want the orchestrator to present a synthesized, human-friendly summary of the final dashboard plan and any next steps so the system can be integrated into a UI or CLI easily.

---

## 4. Functional Requirements

### 4.1 Orchestrator Agent as Root Entry Point

1. The system must introduce a **Dashboard Orchestrator Agent** that serves as the **root agent** exposed via `src/agent.py` for Google ADK.
2. The orchestrator must be implemented as an ADK agent (likely an `LlmAgent` or a combination of a custom agent plus `SequentialAgent`) that can have sub-agents (Data Analysis Agent, Planner Agent).
3. The orchestrator must be invocable programmatically as the main entrypoint for the dashboard-building flow (e.g., from existing app/CLI layers).

### 4.2 Initial User Interaction & Goal Collection

4. The orchestrator must initiate a conversation (or be passed equivalent structured input) to collect at least:
   - High-level goal (e.g., “Monitor customer attrition”).
   - Target audience.
   - Primary use case.
   - Constraints (list of strings).
5. The orchestrator must confirm with the user that input data has been uploaded and is accessible (e.g., a path to a CSV file or dataset location).
6. If data is missing or invalid, the orchestrator must ask the user to correct or upload the required data before proceeding.

### 4.3 Data Analysis Phase

7. After collecting sufficient goal and data information, the orchestrator must call the **Data Analysis Agent** as a sub-agent, passing any necessary state (including `run_dir` and dataset location).
8. The Data Analysis Agent must return a `DataAnalysisOutput` object with:
   - `success: bool`.
   - `additional_questions: list[str]`.
   - `additional_artifacts_path: list[str]` (initially sandbox-relative paths).
9. If `success == False`, the orchestrator must:
   - Surface `additional_questions` to the user.
   - Collect user responses.
   - Re-invoke the Data Analysis Agent, or otherwise terminate gracefully if further progress is impossible.
10. Upon `success == True`, the orchestrator must ensure that required artifacts are available in a **local run directory**, including:
    - `data_profile.md`.
    - `cleaning_summary.md`.
    - Optionally, other important artifacts (e.g., `cleaned.csv`, additional metrics).

### 4.4 Artifact Management and Local vs Remote Paths

11. The system must ensure that artifacts created in the Daytona sandbox are **copied** to a local per-run directory (e.g., `runs/<timestamp>/...`) as part of the Data Analysis Agent’s post-processing (as already partially implemented).
12. The orchestrator (and/or supporting utilities) must provide a way to **map sandbox-relative paths** in `additional_artifacts_path` to corresponding local paths.
13. The planner-related tools and helper functions that currently read from remote/sandbox locations must be updated or extended to support reading from the local run directory; tools originally designed for the Data Analysis Agent may be reused by the Planner with small adjustments.
14. The system must define a convention for **“important” analysis artifacts**:
    - Required: `data_profile.md` and `cleaning_summary.md`.
    - Optional: additional artifacts that are intentionally placed in a designated directory (e.g., `artifacts/data_analysis/important/`) or written via dedicated tools.
15. The orchestrator must build a filtered list of additional artifacts (e.g., important metrics, derived feature summaries) from `additional_artifacts_path` to pass to the Planner, avoiding unnecessary or noisy files.

### 4.5 Planner Handoff and Structured Output

1.  The orchestrator must construct the Planner handoff message, ensuring the following are included:
    - User goal, audience, primary use case, and constraints.
    - Path to `data_profile.md`.
    - Path to `cleaning_summary.md`.
    - Paths describing additional artifacts and/or metrics (from curated local paths).
    In the new design, the orchestrator is responsible for constructing this handoff message directly (without needing backwards compatibility with older formats), including only the information that is truly important for planning a useful dashboard.
2.  The Planner Agent must produce a **structured JSON output** with the following schema (conceptual shape):

    ```json
    {
      "dashboard_spec_path": "path_to_dashboard_spec.json",
      "needs_additional_analysis": null,
      "needs_user_clarification": null,
      "meta": {
        "primary_goal": "Monitor customer attrition",
        "notable_segments": [
          "High balance, low activity",
          "New customers < 6 months"
        ],
        "visual_count": 6
      }
    }
    ```

3.  `dashboard_spec_path` must be a local path pointing to a JSON file created by planner tooling (for example, via `create_dashboard` in `src/tools/planner.py`), stored under the run directory (e.g., `runs/<timestamp>/planner/dashboard_spec.json`).
4.  `needs_additional_analysis` must be either:
    - `null`/empty when no further analysis is needed, or
    - An array of strings describing additional analyses the Data Analysis Agent should perform.
5.  `needs_user_clarification` must be either:
    - `null`/empty when no further clarification is needed, or
    - An array of user-facing questions that the orchestrator should surface.

### 4.6 Orchestrator as Mediator (Follow-ups)

21. If `needs_user_clarification` is non-empty, the orchestrator must:
    - Surface each question to the user.
    - Collect the user’s answers.
    - Optionally re-invoke the Planner with updated context, or present the outstanding questions as part of the final output if re-planning is out of scope for v1.
22. If `needs_additional_analysis` is non-empty, the orchestrator must:
    - Either re-invoke the Data Analysis Agent with the requested analyses (v1 may restrict this to a simple re-run or a no-op with clear TODO messaging).
    - Or include these requested analyses as **next steps** in the final orchestrator output for manual execution.

### 4.7 Final Response and Summary

23. After a Planner run that does not require further user interaction (or after follow-ups are resolved), the orchestrator must:
    - Return the structured Planner output (including `dashboard_spec_path`, `needs_*` fields, and `meta`).
    - Provide a synthesized, user-friendly summary of:
      - The dashboard’s main purpose and target audience.
      - Key insights from the data profile and cleaning summary.
      - Overview of planned visuals/sections (based on `meta.visual_count` and any dashboard spec contents).
      - Any remaining open questions or suggested next steps.
24. The orchestrator must be capable of running as a single ADK agent invocation that encapsulates this full flow (from initial user goal to final planner output), so downstream consumers do not need to orchestrate sub-agent calls themselves.

---

## 5. Non-Goals (Out of Scope)

1. Designing or implementing a full web UI or chat frontend; this PRD focuses on the agent-level orchestration and structured outputs.
2. Defining the complete schema of the dashboard spec JSON; only the existence and path (`dashboard_spec_path`) are required here.
3. Implementing complex multi-iteration loops between Planner and Data Analysis Agent beyond a simple “one follow-up round” (v1 may support at most one additional interaction cycle).
4. Advanced error recovery or retry logic for failures inside the Data Analysis Agent or Planner Agent beyond basic failure reporting and messaging.
5. Adding new metric computations or domain-specific analytics; these can be added later as new tools or analysis steps.

---

## 6. Design Considerations

- **ADK Multi-Agent Patterns**:
  - The orchestrator may be a single `LlmAgent` that uses tools to invoke sub-agents, or a composed **workflow agent** (e.g., `SequentialAgent`) whose sub-agents are:
    1. A goal-intake / validation agent.
    2. The Data Analysis Agent.
    3. The Planner Agent.
  - Shared state (`InvocationContext.session.state`) should be used to pass `run_dir`, dataset location, analysis outputs, and planner outputs along the pipeline.
- **State Keys and Output Keys**:
  - Reuse or extend existing output keys (`data_analysis_output`, etc.) so the orchestrator can reliably read Data Analysis Agent results.
  - Define a clear output key for the Planner output (e.g., `planner_output`) to simplify orchestrator logic.
- **File Organization**:
  - Maintain the existing `runs/<timestamp>/...` structure for artifacts.
  - Consider a dedicated subdirectory for “planner-relevant analysis artifacts” (e.g., `artifacts/data_analysis/planner_ready/`) or a convention where Data Analysis Agent writes a consolidated JSON summary via a dedicated tool.
- **User Prompt Design**:
  - Prompts for the orchestrator should clearly describe its role as coordinator and mediator, including how it distinguishes:
    - Messages destined for the user (e.g., clarifying questions, summaries, errors).
    - Messages destined for sub-agents (e.g., detailed technical instructions or analysis/planning requests).
  - The orchestrator should surface user-facing messages to the user, and agent-facing messages only to the respective sub-agent (Data Analysis Agent or Planner).
- **Extensibility**:
  - The orchestrator’s design should allow additional sub-agents (e.g., visualization generator, report writer) to be added later without breaking the core flow.
 - **Per-Agent Conversation History**:
  - Each agent (orchestrator, Data Analysis Agent, Planner) should retain its own message history to reduce token usage and avoid mixing contexts.
  - When the orchestrator delegates a task to a sub-agent, it should behave like a user speaking directly to that agent, sending a concise, context-rich prompt rather than forwarding the entire orchestrator transcript.

---

## 7. Technical Considerations

1. **Google ADK Integration**:
   - The orchestrator must be implemented using ADK primitives (`LlmAgent`, `SequentialAgent`, etc.) following the patterns in the multi-agent documentation.
   - `src/agent.py` must expose the orchestrator as the `root_agent` used by Google ADK.
2. **Daytona Sandbox vs Local FS**:
   - The Data Analysis Agent currently copies artifacts from the Daytona sandbox to a local artifacts directory via `DaytonaSandboxSingleton().copy_workspace_to_artifacts`.
   - The orchestrator and Planner must rely on **local paths** for reading `data_profile.md`, `cleaning_summary.md`, and other artifacts.
   - Any functions or tools that still assume sandbox-relative paths must be updated or wrapped to accept local paths, possibly by a path-mapping utility.
3. **Planner Tools**:
   - Existing planner tools (e.g., `create_dashboard_tool` in `src/tools/planner.py`) must be reused to persist planner outputs (e.g., `dashboard_spec.json`) under the run directory.
   - The planner output schema should reference this path as `dashboard_spec_path`.
4. **Schema Definitions**:
   - Structured outputs (e.g., Planner output) should be modeled as Pydantic models (similar to `DataAnalysisOutput`) to ensure type safety and consistent JSON serialization.
   - The dashboard spec JSON may use a custom schema that will later be interpreted and enforced by the UI/API layer (e.g., Flask/Next.js), rather than conforming to a pre-existing dashboard framework.
5. **Testing and Observability**:
   - The orchestrator should be testable in isolation by mocking the Data Analysis Agent and Planner Agent.
   - Logging/tracing (e.g., via Phoenix) should cover critical steps: data confirmation, analysis run, planner handoff, and final response.
6. **Execution Limits and Reliability**:
   - Each agent should be configured with a maximum number of tool/function calls (target ~15 per agent) to prevent runaway tool use.
   - Agent invocations should include timeouts in the range of 5–10 minutes; on timeout, the orchestrator must surface a clear timeout message to the user.
   - For recoverable failures, the system should perform at most 2 retries per critical step (e.g., Data Analysis or Planner execution); if still unsuccessful, the orchestrator must stop and clearly report the failure and context to the user.

---

## 8. Success Metrics

1. **Functional Success**:
   - Given a valid dataset and reasonable goal description, a single invocation of the orchestrator produces:
     - A valid `dashboard_spec_path` pointing to an existing JSON file.
     - A populated `meta` object (e.g., `primary_goal`, `visual_count`).
     - A user-facing summary of the planned dashboard.
2. **Developer Experience**:
   - Internal engineers can add the orchestrator as the only root agent in `src/agent.py` and no longer have to manually orchestrate planner and data analysis runs.
   - Adding a new analysis artifact type for planner consumption requires at most changes in the Data Analysis Agent output and a small mapping in the orchestrator (no major refactors).
3. **Reliability and Clarity**:
   - Planner runs rarely fail due to missing `data_profile` or `cleaning_summary` artifacts.
   - When more information is needed, `needs_additional_analysis` and `needs_user_clarification` are populated and surfaced clearly by the orchestrator.

---

## 9. Open Questions

1. **Planner Re-Invocation Strategy and Message Routing**:
   - When `needs_additional_analysis` or `needs_user_clarification` are non-empty, to what extent should the orchestrator:
     - Fully handle multi-round loops (re-running Data Analysis and Planner), versus
     - Limiting itself to a single pass and exposing the needed work to the user?
   - What is the precise pattern for surfacing messages:
     - User-facing clarifications and summaries should go only to the user.
     - Agent-facing technical instructions and follow-ups should go only to the relevant sub-agent (Data Analysis Agent or Planner).
2. **Artifact Filtering and Metrics Hybrid Mechanism**:
   - The direction is a hybrid approach:
     - If the Data Analysis Agent computes additional metrics, it should use a dedicated tool to write a summarized artifact (e.g., a metrics summary file).
     - When metrics are not part of `cleaned.csv`, the Data Analysis Agent must also persist these metrics artifacts under the `cleaned` (or another clearly defined) folder for downstream consumption.
   - Remaining questions:
     - Exact naming and location conventions for these summary files.
     - How strictly to enforce these conventions at runtime (e.g., validation).
3. **User Interaction Channel**:
   - In the near term, the orchestrator will be wired into the simple chat UI exposed by Google ADK via the root agent.
   - Later, it is expected to be included behind a Flask API and surfaced in a Next.js UI, but these integrations are out of scope for this PRD.
4. **Dashboard Spec Format**:
   - The dashboard spec will use a custom JSON schema; the exact structure and validation rules will be defined and interpreted later by the UI developers.
   - Open: what minimal constraints (e.g., IDs, chart types, layout hints) should be baked into the schema now to avoid breaking changes later.
5. **Error Handling, Limits, and Timeouts**:
   - While this PRD defines rough limits (max ~15 tool calls per agent, 5–10 minute timeouts, up to 2 retries), the exact thresholds may need tuning based on real-world usage.
   - Open: should these limits be configurable per environment (e.g., dev vs. prod) and how should configuration be surfaced (env vars, config files, etc.)?
