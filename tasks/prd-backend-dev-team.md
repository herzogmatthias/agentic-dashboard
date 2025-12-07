# PRD: Backend Dev Team Feature

## Introduction/Overview

The Backend Dev Team feature introduces a new agent architecture for implementing dashboard backends in a structured, team-based approach. At the core is a **Backend Planner Agent** that analyzes the dashboard concept, data profile, and metrics summary to create a comprehensive todo list of backend artifacts (API routes, helpers). This todo list is then executed by a trio of specialized agents (Backend Dev, Tester, QA) working in an iterative loop until each artifact passes validation.

**Problem Solved:** Currently, the backend implementation is handled by a single agent that must juggle planning, implementation, testing, and validation. This leads to context overload and inconsistent quality. By separating concerns into specialized agents with a planning phase, we get better structure, testability, and the ability to iterate on individual artifacts until they meet quality standards.

---

## Goals

1. **Create a Backend Planner Agent** that produces a structured `PlannerTodoList` with all required artifacts for a dashboard backend
2. **Establish a new agent folder structure** (`src/agents/backend_dev_team/`) to house all team agents
3. **Build a boilerplate Loop Agent** that coordinates the Dev → Tester → QA cycle for each artifact
4. **Persist the todo list** as JSON for debugging and as session state for runtime access
5. **Enable orchestrator integration** so the Backend Planner can be called after dashboard concept completion

---

## User Stories

### US-1: Orchestrator triggers Backend Planner

**As** the main orchestrator  
**I want** to call the Backend Planner Agent after the dashboard concept is complete  
**So that** a structured implementation plan is created before any backend code is written

### US-2: Backend Planner creates todo list

**As** the Backend Planner Agent  
**I want** to analyze the dashboard concept, data profile, and metrics summary  
**So that** I can create a comprehensive `PlannerTodoList` with all required API routes and helpers

### US-3: Todo list persistence

**As** a developer debugging the system  
**I want** the todo list saved as a JSON file in the run directory  
**So that** I can inspect the planned artifacts and track progress

### US-4: Loop Agent coordinates artifact implementation

**As** the Loop Agent  
**I want** to hand off each artifact to the Dev → Tester → QA trio  
**So that** artifacts are implemented, tested, and validated iteratively until they pass

### US-5: Iterative artifact refinement

**As** the QA Agent (future)  
**I want** to fail an artifact and send it back to the Dev Agent  
**So that** issues are fixed before the artifact is marked complete

---

## Functional Requirements

### Backend Planner Agent

1. **FR-1:** The Backend Planner Agent MUST be located at `src/agents/backend_dev_team/planner/agent.py`

2. **FR-2:** The Backend Planner Agent MUST receive context (dashboard concept, data profile, metrics summary) via auto-injection in the prompt or before_model_callback

3. **FR-3:** The Backend Planner Agent MUST have a `create_backend_todo_list` tool that:

   - Accepts the planned artifacts as structured input
   - Validates the input against the `PlannerTodoList` Pydantic model
   - Saves the todo list as JSON to `{run_dir}/backend_dev_team/backend_todos.json`
   - Stores the todo list in session state under key `backend_todo_list`
   - Returns confirmation with the file path and artifact count

4. **FR-4:** The Backend Planner Agent MUST output artifacts that conform to the `PlannerArtifactTodo` schema, including:

   - Unique `id` for each artifact
   - `kind` (route or helper)
   - `title` and `description`
   - `http_path` and `http_method` for routes
   - `query_params` with type, required flag, and descriptions
   - `expected_shape` defining the JSON response structure
   - `depends_on` for dependency ordering
   - `priority` for execution order

5. **FR-5:** System-maintained fields (`status`, `created_at`, `updated_at`, `run_id`) MUST be set by the tool, not by the LLM

### Loop Agent (Boilerplate)

6. **FR-6:** The Loop Agent MUST be located at `src/agents/backend_dev_team/loop/agent.py`

7. **FR-7:** The Loop Agent MUST be structured to support handoffs to three sub-agents:

   - Backend Dev Agent (placeholder)
   - Tester Agent (placeholder)
   - QA Agent (placeholder)

8. **FR-8:** The Loop Agent MUST implement an iterative cycle:

   - Pick next pending artifact from todo list
   - Hand off to Dev Agent
   - Hand off to Tester Agent
   - Hand off to QA Agent
   - If QA fails, cycle back to Dev Agent
   - If QA passes, mark artifact as `done` and proceed to next

9. **FR-9:** The Loop Agent MUST update artifact `status` in the todo list as work progresses:

   - `pending` → `in_progress` when work begins
   - `in_progress` → `done` when QA passes
   - `in_progress` → `failed` if max retries exceeded

10. **FR-10:** The Loop Agent boilerplate MUST include empty tool stubs for:
    - `get_next_artifact` - retrieves next pending artifact
    - `update_artifact_status` - updates status in todo list
    - `handoff_to_dev` - placeholder for dev agent handoff
    - `handoff_to_tester` - placeholder for tester agent handoff
    - `handoff_to_qa` - placeholder for QA agent handoff

### Folder Structure

11. **FR-11:** The new agent folder structure MUST be:
    ```
    src/agents/backend_dev_team/
    ├── __init__.py
    ├── planner/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── prompts.py
    │   └── tools.py
    ├── loop/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── tools.py
    ├── dev/
    │   ├── __init__.py
    │   └── agent.py (placeholder)
    ├── tester/
    │   ├── __init__.py
    │   └── agent.py (placeholder)
    └── qa/
        ├── __init__.py
        └── agent.py (placeholder)
    ```

### State Management

12. **FR-12:** The todo list MUST be stored in session state with key `backend_todo_list`

13. **FR-13:** The JSON file MUST be saved at `{run_dir}/backend_dev_team/backend_todos.json`

14. **FR-14:** The todo list MUST be updated (both file and state) whenever an artifact status changes

---

## Non-Goals (Out of Scope)

1. **Full implementation of Dev, Tester, QA agents** - Only placeholders/boilerplate for this phase
2. **Automatic orchestrator integration** - The wiring to call Backend Planner from orchestrator is out of scope; manual invocation is sufficient
3. **Parallel artifact processing** - Artifacts will be processed sequentially
4. **UI/Dashboard for todo list visualization** - JSON file is sufficient for debugging
5. **Retry limit configuration** - Hardcoded defaults are acceptable

---

## Design Considerations

### Agent Communication

- Backend Planner hands off to Loop Agent via ADK's `transfer_to_agent` or by returning a structured result
- Loop Agent manages sub-agent handoffs internally
- All agents share session state for todo list access

### Context Injection

- Backend Planner receives context (dashboard concept, data profile, metrics summary) similar to existing Backend Agent
- Context is minified JSON injected via `before_model_callback`

### Pydantic Models

- Use existing `PlannerTodoList` and `PlannerArtifactTodo` from `src/models/backend_planner_todos.py`
- Tool validates output against these models before saving

---

## Technical Considerations

### Dependencies

- Google ADK for agent orchestration
- Pydantic for model validation
- Existing context loading utilities from `src/agents/utils.py`

### Integration Points

- Backend Planner reads from: `{run_dir}/planner/dashboard_concept.json`, `{run_dir}/data_profile.md`, `{run_dir}/metrics_summary.json`
- Backend Planner writes to: `{run_dir}/backend_dev_team/backend_todos.json`
- Loop Agent reads/updates: `backend_todo_list` in session state

### Model Selection

- Backend Planner: Use reasoning model (similar to existing Planner Agent)
- Loop Agent: Can use lighter model since it's primarily coordination logic

---

## Success Metrics

1. **Todo List Quality:** Backend Planner generates valid `PlannerTodoList` with all required fields for 90%+ of dashboard concepts
2. **Artifact Coverage:** Generated artifacts cover all KPIs and charts defined in the dashboard concept
3. **Schema Compliance:** 100% of generated artifacts pass Pydantic validation
4. **File Persistence:** Todo list JSON is correctly saved and readable for debugging
5. **Loop Agent Ready:** Boilerplate supports adding real agent implementations without structural changes

---

## Resolved Questions

1. **Model selection for Backend Planner** - Use a GPT-5 model for the Backend Planner Agent.

2. **Max retries for QA loop** - An artifact can cycle through Dev → Tester → QA up to **5 times** before being marked `failed`.

3. **Handoff mechanism** - The Loop Agent will use a **structured output approach** rather than ADK native handoffs. The loop runs sequentially through Dev → Tester → QA, using structured outputs from each agent to determine success/failure and whether to cycle back. This avoids complex handoff wiring and keeps control flow explicit.

4. **Helper artifact handling** - The **Planner decides** the implementation order via `depends_on` and `priority` fields. The agent trio processes artifacts in the order specified. However, the trio **can create additional helpers on-demand** if they determine they need them during implementation (these would be ad-hoc, not tracked in the todo list).
