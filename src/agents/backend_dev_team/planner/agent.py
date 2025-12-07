"""
Backend Planner Agent - Creates the todo list of backend artifacts.

This agent analyzes the dashboard concept, data profile, and metrics summary
to create a comprehensive todo list of backend artifacts (API routes, helpers)
that need to be implemented by the Dev → Tester → QA trio.

Uses PlanReActPlanner for structured multi-step reasoning with GPT-5 model.
"""

from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner, PlanReActPlanner
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import ThinkingConfig, ThinkingLevel
from phoenix.otel import register as register_phoenix
from src.core.logging import get_logger
from src.agents.backend_dev_team.planner.callbacks import (
    inject_planner_context_callback,
    initialize_planner_state,
    planner_instruction_provider,
    # State keys
    STATE_KEY_RUN_ID,
    STATE_KEY_RUN_DIR,
    STATE_KEY_BACKEND_TODO_LIST,
    STATE_KEY_BACKEND_TODOS_PATH,
    DEFAULT_TEST_RUN_DIR,
)
from src.agents.backend_dev_team.planner.tools import create_backend_todo_list_tool
tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)
logger = get_logger(__name__)

# Model configuration - GPT-5 for planning
PLANNER_MODEL = "gpt-5.1"


def create_backend_planner_agent() -> LlmAgent:
    """
    Create the Backend Planner Agent.
    
    The Backend Planner Agent:
    - Receives context (dashboard concept, data profile, metrics summary) via callback
    - Analyzes the context to identify required backend artifacts
    - Creates a structured todo list using the create_backend_todo_list tool
    
    Uses PlanReActPlanner for structured multi-step reasoning. The planner
    automatically injects planning instructions.
    
    Returns:
        Configured LlmAgent instance
    """
    model = LiteLlm(model=PLANNER_MODEL, reasoning_effort="medium", timeout=300)
    
    agent = LlmAgent(
        name="backend_planner",
        model=model,
        planner=BuiltInPlanner(thinking_config= ThinkingConfig(include_thoughts=True, thinking_level=ThinkingLevel.HIGH)),
        instruction=planner_instruction_provider,
        tools=[create_backend_todo_list_tool],
        before_agent_callback=initialize_planner_state,
        before_model_callback=inject_planner_context_callback,
    )
    
    logger.info(
        "Backend Planner Agent created",
        extra={"agent": "backend_planner", "phase": "create", "model": PLANNER_MODEL}
    )
    
    return agent


def get_backend_planner_agent() -> LlmAgent:
    """Get a configured Backend Planner Agent instance."""
    return create_backend_planner_agent()
