from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from typing import Optional
from phoenix.otel import register as register_phoenix
from src.core.logging import get_logger

from src.models.planner_output import PlannerOutput
from src.prompts.system_prompts import build_planner_agent_prompt
from src.tools.planner import create_dashboard_tool
from src.tools.filesystem import (
    inspect_json_keys_tool,
    inspect_json_value_tool,
    read_snippet_tool,
)

OUTPUT_KEY = "planner_output"


tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)


def create_planner_agent() -> LlmAgent:
    model = LiteLlm(model="gpt-5-mini")

    agent = LlmAgent(
        name="planner_agent",
        model=model,
        instruction=build_planner_agent_prompt(),
        tools=[
            create_dashboard_tool,
            inspect_json_keys_tool,
            inspect_json_value_tool,
            read_snippet_tool,
        ],
        include_contents='none',
        before_agent_callback=inject_planner_handoff,
        output_key=OUTPUT_KEY,
        output_schema=PlannerOutput,
        description="Designs dashboard concepts based on data analysis artifacts.",
    )

    return agent


def inject_planner_handoff(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Inject temp:planner_handoff from state into the agent's context.
    
    The orchestrator sets temp:planner_handoff via prepare_planner tool.
    This callback reads that state and injects it as a user message with the full context.
    
    Returns:
        Content with handoff message to inject, or None if no handoff found
    """
    try:
        handoff = callback_context.state.get("temp:planner_handoff")
        if handoff:
            logger.info("Injecting planner handoff from temp state", extra={"agent": "planner", "phase": "before_agent"})
            return types.Content(
                role="user",
                parts=[types.Part(text=handoff)]
            )
        else:
            logger.warning("No temp:planner_handoff found in state", extra={"agent": "planner", "phase": "before_agent"})
            return None
    except Exception as e:
        logger.exception("Error injecting planner handoff", extra={"agent": "planner", "phase": "before_agent"})
        return None
