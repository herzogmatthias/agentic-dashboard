"""
Backend Dev Team package.

This package contains the agent team responsible for implementing dashboard backends:
- Planner: Creates the todo list of artifacts to build
- Loop: Coordinates the Dev → Tester → QA cycle
- Dev: Implements backend artifacts
- Tester: Writes and runs tests for artifacts
- QA: Validates artifacts meet quality standards (placeholder)
"""

from src.agents.backend_dev_team.planner import (
    # Agent factory
    create_backend_planner_agent,
    get_backend_planner_agent,
    PLANNER_MODEL,
    # State keys
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_BACKEND_TODO_LIST,
    STATE_KEY_BACKEND_TODOS_PATH,
    DEFAULT_TEST_RUN_DIR,
    # Callbacks
    inject_planner_context_callback,
    initialize_planner_state,
    planner_instruction_provider,
    # Prompts
    build_backend_planner_prompt,
    # Tools
    create_backend_todo_list,
    create_backend_todo_list_tool,
    BACKEND_DEV_TEAM_DIR,
    BACKEND_TODOS_FILENAME,
)

from src.agents.backend_dev_team.tester import (
    # Agent factory
    create_tester_agent,
    get_tester_agent,
    TESTER_MODEL,
    # Prompt builder
    build_tester_prompt,
    # State keys
    STATE_KEY_CURRENT_ARTIFACT,
    STATE_KEY_DEV_RESULT,
    STATE_KEY_TESTER_RESULT,
    STATE_KEY_PREVIOUS_TEST_SUMMARY,
    STATE_KEY_WORKSPACE_ROOT,
    STATE_KEY_DEV_REPORT_PATH,
    STATE_KEY_CLEANED_DATA_FILES,
)

__all__ = [
    # Planner Agent
    "create_backend_planner_agent",
    "get_backend_planner_agent",
    "PLANNER_MODEL",
    # State keys (planner)
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_BACKEND_TODO_LIST",
    "STATE_KEY_BACKEND_TODOS_PATH",
    "DEFAULT_TEST_RUN_DIR",
    # Callbacks
    "inject_planner_context_callback",
    "initialize_planner_state",
    "planner_instruction_provider",
    # Prompts (planner)
    "build_backend_planner_prompt",
    # Tools (planner)
    "create_backend_todo_list",
    "create_backend_todo_list_tool",
    "BACKEND_DEV_TEAM_DIR",
    "BACKEND_TODOS_FILENAME",
    # Tester Agent
    "create_tester_agent",
    "get_tester_agent",
    "TESTER_MODEL",
    "build_tester_prompt",
    # State keys (tester)
    "STATE_KEY_CURRENT_ARTIFACT",
    "STATE_KEY_DEV_RESULT",
    "STATE_KEY_TESTER_RESULT",
    "STATE_KEY_PREVIOUS_TEST_SUMMARY",
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_DEV_REPORT_PATH",
    "STATE_KEY_CLEANED_DATA_FILES",
]