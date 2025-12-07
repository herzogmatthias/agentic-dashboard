"""
Backend Dev Team package.

This package contains the agent team responsible for implementing dashboard backends:
- Planner: Creates the todo list of artifacts to build
- Loop: Coordinates the Dev → Tester → QA cycle
- Dev: Implements backend artifacts (placeholder)
- Tester: Writes tests for artifacts (placeholder)
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

__all__ = [
    # Planner Agent
    "create_backend_planner_agent",
    "get_backend_planner_agent",
    "PLANNER_MODEL",
    # State keys
    "STATE_KEY_RUN_ID",
    "STATE_KEY_RUN_DIR",
    "STATE_KEY_BACKEND_TODO_LIST",
    "STATE_KEY_BACKEND_TODOS_PATH",
    "DEFAULT_TEST_RUN_DIR",
    # Callbacks
    "inject_planner_context_callback",
    "initialize_planner_state",
    "planner_instruction_provider",
    # Prompts
    "build_backend_planner_prompt",
    # Tools
    "create_backend_todo_list",
    "create_backend_todo_list_tool",
    "BACKEND_DEV_TEAM_DIR",
    "BACKEND_TODOS_FILENAME",
]