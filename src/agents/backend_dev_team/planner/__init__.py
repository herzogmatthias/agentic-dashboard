"""
Backend Planner Agent package.

The Planner Agent analyzes the dashboard concept, data profile, and metrics summary
to create a structured todo list of backend artifacts (API routes, helpers).
"""

from src.agents.backend_dev_team.planner.agent import (
    create_backend_planner_agent,
    get_backend_planner_agent,
    PLANNER_MODEL,
)
from src.agents.backend_dev_team.planner.callbacks import (
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_BACKEND_TODO_LIST,
    STATE_KEY_BACKEND_TODOS_PATH,
    DEFAULT_TEST_RUN_DIR,
    inject_planner_context_callback,
    initialize_planner_state,
    planner_instruction_provider,
)
from src.agents.backend_dev_team.planner.prompts import build_backend_planner_prompt
from src.agents.backend_dev_team.planner.tools import (
    create_backend_todo_list,
    create_backend_todo_list_tool,
    BACKEND_DEV_TEAM_DIR,
    BACKEND_TODOS_FILENAME,
)

__all__ = [
    # Agent factory
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