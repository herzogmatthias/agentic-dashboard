# Tasks: Backend Dev Team Feature

## Relevant Files

- `src/agents/backend_dev_team/__init__.py` - Package init, exports main agents
- `src/agents/backend_dev_team/planner/__init__.py` - Planner subpackage init
- `src/agents/backend_dev_team/planner/agent.py` - Backend Planner Agent implementation
- `src/agents/backend_dev_team/planner/prompts.py` - System prompts for the planner
- `src/agents/backend_dev_team/planner/tools.py` - create_backend_todo_list tool
- `src/agents/backend_dev_team/planner/callbacks.py` - Context injection callbacks
- `src/agents/backend_dev_team/loop/__init__.py` - Loop subpackage init
- `src/agents/backend_dev_team/loop/agent.py` - Custom BackendDevLoopAgent (BaseAgent) with smart routing
- `src/agents/backend_dev_team/loop/tools.py` - State keys, exit_loop tool, state helpers
- `src/agents/backend_dev_team/loop/callbacks.py` - State injection callbacks for sub-agents
- `src/models/backend_planner_todos.py` - Existing Pydantic models (PlannerTodoList, PlannerArtifactTodo)
- `src/models/backend_planner_input.py` - Barebone input models for ADK tool compatibility
- `tests/agents/backend_dev_team/__init__.py` - Test package init
- `tests/agents/backend_dev_team/test_planner_agent.py` - Tests for Backend Planner Agent
- `tests/agents/backend_dev_team/test_planner_tools.py` - Tests for create_backend_todo_list tool
- `tests/agents/backend_dev_team/test_loop_agent.py` - Tests for Loop Agent

### Notes

- Unit tests should be placed in `tests/agents/backend_dev_team/` mirroring the source structure
- Use `python -m pytest tests/agents/backend_dev_team/ -v` to run tests for this feature
- The existing `src/models/backend_planner_todos.py` contains the Pydantic models to use
- Backend Planner uses GPT-5 model (gpt-5.1)
- Loop Agent uses custom BaseAgent with max_iterations=5
- Sub-agents (Dev, Tester, QA) are integrated into loop/agent.py with structured output schemas
- Dev/Tester/QA directories are NOT used - sub-agents live in loop/agent.py

## Architecture

### Flow

```
Planner → injects artifact to state → Loop(Dev ↔ Tester ↔ QA) → result in state → Planner reads result
```

### Loop Agent Routing Logic

- **Route artifacts** (`kind="route"`): Dev → Tester → QA (full cycle)
- **Helper artifacts** (`kind="helper"`): Dev → Tester only (skip QA)
- **On Tester failure**: Route back to Dev immediately (don't proceed to QA)
- **On QA failure**: Route back to Dev immediately
- **Max iterations**: 5 cycles before marking as failed

### Structured Output Schemas

- `DevResult`: success, files_created, code_summary, error_message
- `TesterResult`: success, tests_passed, test_files, test_count, failure_message, error_message
- `QAResult`: passed, issues, recommendations, error_message

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:

- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 1.0 Create folder structure for backend_dev_team agents

  - [x] 1.1 Create `src/agents/backend_dev_team/` directory
  - [x] 1.2 Create `src/agents/backend_dev_team/__init__.py` with package exports
  - [x] 1.3 Create `src/agents/backend_dev_team/planner/` directory with `__init__.py`
  - [x] 1.4 Create `src/agents/backend_dev_team/loop/` directory with `__init__.py`
  - [x] 1.5 Create `src/agents/backend_dev_team/dev/` directory with `__init__.py`
  - [x] 1.6 Create `src/agents/backend_dev_team/tester/` directory with `__init__.py`
  - [x] 1.7 Create `src/agents/backend_dev_team/qa/` directory with `__init__.py`
  - [x] 1.8 Create `tests/agents/backend_dev_team/` directory with `__init__.py`

- [x] 2.0 Implement Backend Planner Agent

  - [x] 2.1 Create `src/agents/backend_dev_team/planner/prompts.py` with system prompt that instructs the LLM to analyze context and output artifacts conforming to PlannerArtifactTodo schema
  - [x] 2.2 Create `src/agents/backend_dev_team/planner/callbacks.py` with context injection callback (load dashboard_concept, data_profile, metrics_summary)
  - [x] 2.3 Create `src/agents/backend_dev_team/planner/agent.py` with LlmAgent using GPT-5 model, PlanReActPlanner, instruction provider, and before_model_callback
  - [x] 2.4 Update `src/agents/backend_dev_team/planner/__init__.py` to export agent factory functions
  - [x] 2.5 Define state keys for planner (STATE_KEY_BACKEND_TODO_LIST, STATE_KEY_BACKEND_TODOS_PATH)

- [x] 3.0 Implement create_backend_todo_list tool

  - [x] 3.1 Create `src/agents/backend_dev_team/planner/tools.py` with create_backend_todo_list function
  - [x] 3.2 Implement input validation against PlannerTodoList Pydantic model
  - [x] 3.3 Implement system field population (run_id, created_at, updated_at, status=pending)
  - [x] 3.4 Implement JSON file persistence to `{run_dir}/backend_dev_team/backend_todos.json`
  - [x] 3.5 Implement session state storage under key `backend_todo_list`
  - [x] 3.6 Return confirmation with file path and artifact count
  - [x] 3.7 Create FunctionTool wrapper and add to planner agent tools list
  - [x] 3.8 Create barebone input models in `src/models/backend_planner_input.py` (ADK can't parse datetime fields)
  - [x] 3.9 Add metrics_ref validation against dashboard_concept.json IDs

- [x] 4.0 Implement Custom Loop Agent (BackendDevLoopAgent)

  - [x] 4.1 Create `src/agents/backend_dev_team/loop/tools.py` with:
    - State keys (STATE_KEY_CURRENT_ARTIFACT, STATE_KEY_LOOP_RESULT, etc.)
    - `exit_loop` tool for signaling loop termination
    - State helper functions (get_current_artifact, set_loop_result, inject_artifact_to_state, etc.)
  - [x] 4.2 Create `src/agents/backend_dev_team/loop/callbacks.py` with:
    - `initialize_loop_state` - validates artifact in state
    - `inject_artifact_context_for_dev/tester/qa` - per-sub-agent context injection
  - [x] 4.3 Create `src/agents/backend_dev_team/loop/agent.py` with:
    - Structured output schemas: `DevResult`, `TesterResult`, `QAResult`
    - Sub-agent factories: `create_dev_agent`, `create_tester_agent`, `create_qa_agent`
    - Custom `BackendDevLoopAgent(BaseAgent)` with `_run_async_impl`
    - Smart routing logic (routes→full cycle, helpers→skip QA, failures→back to Dev)
    - Max iterations constant (5)
  - [x] 4.4 Update `src/agents/backend_dev_team/loop/__init__.py` to export:
    - `BackendDevLoopAgent`, `create_loop_agent`, `get_loop_agent`
    - Sub-agent factories and structured output schemas
    - State keys, constants, and helper functions

- [ ] 5.0 Add tests for Backend Planner and Loop Agent

  - [ ] 5.1 Create `tests/agents/backend_dev_team/test_planner_agent.py`:
    - Test agent creation and configuration
    - Test instruction provider returns valid prompt
    - Test context injection callback
  - [ ] 5.2 Create `tests/agents/backend_dev_team/test_planner_tools.py`:
    - Test create_backend_todo_list validates input
    - Test JSON file is created at correct path
    - Test session state is updated
    - Test system fields are populated correctly
    - Test metrics_ref validation
    - Test returns correct confirmation
  - [ ] 5.3 Create `tests/agents/backend_dev_team/test_loop_agent.py`:
    - Test BackendDevLoopAgent creation with default sub-agents
    - Test BackendDevLoopAgent creation with custom sub-agents
    - Test max_iterations constant is 5
    - Test routing logic (helper skips QA)
    - Test failure routing (tester fail → back to dev)
    - Test structured output schemas (DevResult, TesterResult, QAResult)

- [ ] 6.0 Integration and manual testing
  - [ ] 6.1 Run all new tests with `python -m pytest tests/agents/backend_dev_team/ -v`
  - [ ] 6.2 Run full test suite to ensure no regressions: `python -m pytest tests/ -v`
  - [ ] 6.3 Manually test Backend Planner Agent with existing run directory (e.g., runs/run_20251204_142914)
  - [ ] 6.4 Verify JSON output at `{run_dir}/backend_dev_team/backend_todos.json` is valid and complete
  - [ ] 6.5 Verify all artifacts have required fields populated
  - [ ] 6.6 Test Loop Agent with mock artifact in state
