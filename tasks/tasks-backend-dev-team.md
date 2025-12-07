# Tasks: Backend Dev Team Feature

## Relevant Files

- `src/agents/backend_dev_team/__init__.py` - Package init, exports main agents
- `src/agents/backend_dev_team/planner/__init__.py` - Planner subpackage init
- `src/agents/backend_dev_team/planner/agent.py` - Backend Planner Agent implementation
- `src/agents/backend_dev_team/planner/prompts.py` - System prompts for the planner
- `src/agents/backend_dev_team/planner/tools.py` - create_backend_todo_list tool
- `src/agents/backend_dev_team/planner/callbacks.py` - Context injection callbacks
- `src/agents/backend_dev_team/loop/__init__.py` - Loop subpackage init
- `src/agents/backend_dev_team/loop/agent.py` - Loop Agent boilerplate
- `src/agents/backend_dev_team/loop/tools.py` - Tool stubs for artifact management
- `src/agents/backend_dev_team/dev/__init__.py` - Dev subpackage init
- `src/agents/backend_dev_team/dev/agent.py` - Placeholder Dev Agent
- `src/agents/backend_dev_team/tester/__init__.py` - Tester subpackage init
- `src/agents/backend_dev_team/tester/agent.py` - Placeholder Tester Agent
- `src/agents/backend_dev_team/qa/__init__.py` - QA subpackage init
- `src/agents/backend_dev_team/qa/agent.py` - Placeholder QA Agent
- `src/models/backend_planner_todos.py` - Existing Pydantic models (PlannerTodoList, PlannerArtifactTodo)
- `tests/agents/backend_dev_team/__init__.py` - Test package init
- `tests/agents/backend_dev_team/test_planner_agent.py` - Tests for Backend Planner Agent
- `tests/agents/backend_dev_team/test_planner_tools.py` - Tests for create_backend_todo_list tool
- `tests/agents/backend_dev_team/test_loop_agent.py` - Tests for Loop Agent
- `tests/agents/backend_dev_team/test_loop_tools.py` - Tests for Loop Agent tools

### Notes

- Unit tests should be placed in `tests/agents/backend_dev_team/` mirroring the source structure
- Use `python -m pytest tests/agents/backend_dev_team/ -v` to run tests for this feature
- The existing `src/models/backend_planner_todos.py` contains the Pydantic models to use
- Backend Planner uses GPT-5 model
- Loop Agent max retries is 5 before marking artifact as failed

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

- [ ] 4.0 Implement Loop Agent boilerplate

  - [ ] 4.1 Create `src/agents/backend_dev_team/loop/tools.py` with tool stubs:
    - `get_next_artifact` - retrieve next pending artifact respecting depends_on and priority
    - `update_artifact_status` - update status in both JSON file and session state
  - [ ] 4.2 Create `src/agents/backend_dev_team/loop/agent.py` with:
    - LlmAgent setup (can use lighter model)
    - System prompt explaining the Dev → Tester → QA cycle
    - Max retries constant (5)
    - Sub-agent placeholders structure
  - [ ] 4.3 Update `src/agents/backend_dev_team/loop/__init__.py` to export agent factory functions
  - [ ] 4.4 Implement artifact status transition logic (pending → in_progress → done/failed)

- [ ] 5.0 Create placeholder agents (Dev, Tester, QA)

  - [ ] 5.1 Create `src/agents/backend_dev_team/dev/agent.py` with placeholder DevAgent class and TODO comments
  - [ ] 5.2 Create `src/agents/backend_dev_team/tester/agent.py` with placeholder TesterAgent class and TODO comments
  - [ ] 5.3 Create `src/agents/backend_dev_team/qa/agent.py` with placeholder QAAgent class and TODO comments
  - [ ] 5.4 Update each subpackage `__init__.py` to export placeholder agents
  - [ ] 5.5 Update main `src/agents/backend_dev_team/__init__.py` to export all agents

- [ ] 6.0 Add tests for Backend Planner and Loop Agent

  - [ ] 6.1 Create `tests/agents/backend_dev_team/test_planner_agent.py`:
    - Test agent creation and configuration
    - Test instruction provider returns valid prompt
    - Test context injection callback
  - [ ] 6.2 Create `tests/agents/backend_dev_team/test_planner_tools.py`:
    - Test create_backend_todo_list validates input
    - Test JSON file is created at correct path
    - Test session state is updated
    - Test system fields are populated correctly
    - Test returns correct confirmation
  - [ ] 6.3 Create `tests/agents/backend_dev_team/test_loop_agent.py`:
    - Test agent creation
    - Test max retries constant is 5
  - [ ] 6.4 Create `tests/agents/backend_dev_team/test_loop_tools.py`:
    - Test get_next_artifact returns pending artifact with lowest priority
    - Test get_next_artifact respects depends_on
    - Test update_artifact_status updates both file and state

- [ ] 7.0 Integration and manual testing
  - [ ] 7.1 Run all new tests with `python -m pytest tests/agents/backend_dev_team/ -v`
  - [ ] 7.2 Run full test suite to ensure no regressions: `python -m pytest tests/ -v`
  - [ ] 7.3 Manually test Backend Planner Agent with existing run directory (e.g., runs/run_20251204_142914)
  - [ ] 7.4 Verify JSON output at `{run_dir}/backend_dev_team/backend_todos.json` is valid and complete
  - [ ] 7.5 Verify all artifacts have required fields populated
