"""
Backend Agent - Creates Next.js API routes and TypeScript models.

This agent is responsible for implementing the data layer of the dashboard
by creating API routes, TypeScript models, and utilities in the sample-dashboard
Next.js project.

Uses PlanReActPlanner for structured multi-step reasoning with xai/grok-4-1-fast-non-reasoning-latest.
"""

from google.adk.agents import LlmAgent
from google.adk.planners import PlanReActPlanner
from google.adk.models.lite_llm import LiteLlm
from phoenix.otel import register as register_phoenix

from src.core.logging import get_logger
from src.agents.backend.callbacks import (
    inject_context_callback,
    initialize_backend_state,
    backend_instruction_provider,
    MAX_CONTINUATION_ATTEMPTS,
)
from src.agents.backend.custom_agent import BackendAgentWithContinuation
from src.tools.backend import (
    # Data access tools
    get_sample_rows_tool,
    inspect_json_preview_tool,
    # Creation tools
    create_api_tool,
    create_model_tool,
    # Search tool
    search_content_tool,
    # Validation tools
    run_lint_tool,
    run_type_check_tool,
    # Manifest tool
    write_backend_manifest_tool,
    # MCP toolset factories
    create_filesystem_toolset,
)

tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)

# Model configuration
BACKEND_MODEL = "xai/grok-4-1-fast-non-reasoning-latest"



def create_backend_llm_agent() -> LlmAgent:
    """
    Create the underlying LLM agent for backend development.
    
    Uses PlanReActPlanner for structured multi-step reasoning. The planner
    automatically injects planning instructions, so the prompt should NOT
    include redundant format instructions.
    
    This is the raw LlmAgent without continuation wrapper.
    Use create_backend_agent() for the full agent with continuation support.
    
    Returns:
        Configured LlmAgent instance
    """
    model = LiteLlm(model=BACKEND_MODEL)
    
    tools = [
        # Data access tools
        get_sample_rows_tool,
        inspect_json_preview_tool,
        # Creation tools
        create_api_tool,
        create_model_tool,
        # Search tool
        search_content_tool,
        # Validation tools
        run_lint_tool,
        run_type_check_tool,
        # Manifest tool
        write_backend_manifest_tool,
        # MCP toolsets
        create_filesystem_toolset(),
    ]
    
    agent = LlmAgent(
        name="backend_llm",
        model=model,
        planner=PlanReActPlanner(),
        instruction=backend_instruction_provider,
        tools=tools,
        before_agent_callback=initialize_backend_state,
        before_model_callback=inject_context_callback,
    )
    
    logger.info(
        "Backend LLM agent created",
        extra={"agent": "backend_llm", "phase": "create", "model": BACKEND_MODEL}
    )
    
    return agent


def create_backend_agent(max_continuations: int = MAX_CONTINUATION_ATTEMPTS) -> BackendAgentWithContinuation:
    """
    Create and configure the Backend Agent with continuation support.
    
    The Backend Agent uses:
    - Custom tools for file creation (create_api, create_model)
    - MCP filesystem tools for read/write/edit operations
    - Data access tools (get_sample_rows, inspect_json_preview)
    - Validation tools for lint/build checking
    - Context injection via before_model_callback
    - Automatic continuation on empty responses via custom agent wrapper
    
    Args:
        max_continuations: Maximum number of continuation attempts (default: 3)
    
    Returns:
        Configured BackendAgentWithContinuation instance
    """
    llm_agent = create_backend_llm_agent()
    
    agent = BackendAgentWithContinuation(
        name="backend",
        llm_agent=llm_agent,
        max_continuations=max_continuations,
    )
    
    logger.info(
        "Backend agent with continuation created",
        extra={
            "agent": "backend",
            "phase": "create",
            "max_continuations": max_continuations,
        }
    )
    
    return agent


def get_backend_agent() -> BackendAgentWithContinuation:
    """Get a configured Backend Agent instance with continuation support."""
    return create_backend_agent()


def get_backend_llm_agent() -> LlmAgent:
    """Get the raw Backend LLM Agent without continuation wrapper."""
    return create_backend_llm_agent()
