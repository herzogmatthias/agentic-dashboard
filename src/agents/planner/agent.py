from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.genai import types
from phoenix.otel import register as register_phoenix
from pydantic import ValidationError

from src.core.logging import get_logger
from src.models.planner_output import PlannerOutput
from .prompts import build_planner_agent_prompt
from src.tools.planner import create_dashboard_tool
from src.tools.filesystem import (
    inspect_json_keys_tool,
    inspect_json_value_tool,
    read_snippet_tool,
)
from src.tools.delegation import summarize_actions_tool

OUTPUT_KEY = "planner_output"


tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)


def handle_planner_output_validation(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    After-agent callback to validate planner output.
    
    This callback:
    1. Checks if create_dashboard was called (dashboard_spec_path in state)
    2. Validates the output against PlannerOutput schema
    3. Returns retry instructions if validation fails
    
    Args:
        callback_context: ADK callback context
        
    Returns:
        Content with retry instructions if validation failed, None otherwise
    """
    try:
        state = callback_context.state
        
        # Check if create_dashboard was called
        dashboard_spec_path = state.get("dashboard_spec_path")
        
        if not dashboard_spec_path:
            logger.warning(
                "Planner did not call create_dashboard tool",
                extra={"agent": "planner", "phase": "validation"}
            )
            retry_message = (
                "**Missing Dashboard Specification**\n\n"
                "You must call the `create_dashboard` tool before returning your final response.\n\n"
                "Please:\n"
                "1. Call `create_dashboard` with your dashboard concept\n"
                "2. Then return a JSON response with these fields:\n"
                "   - `meta`: Object with primary_goal, notable_segments, visual_count, kpi_count, has_time_series, complexity\n"
                "   - `summary`: Brief textual summary of the dashboard plan\n\n"
                "Optional fields: `needs_additional_analysis`, `needs_user_clarification`"
            )
            return types.Content(
                role="model",
                parts=[types.Part(text=retry_message)]
            )
        
        # Check if planner_output exists and validate it
        if OUTPUT_KEY in state:
            output = state[OUTPUT_KEY]
            
            # If it's a dict, validate against schema
            if isinstance(output, dict):
                try:
                    PlannerOutput.model_validate(output)
                    # Validation passed
                    logger.info(
                        "Planner output validated successfully",
                        extra={"agent": "planner", "phase": "validation", "path": dashboard_spec_path}
                    )
                    return None
                except ValidationError as e:
                    error_details = str(e)
                    logger.warning(
                        f"Planner output validation failed: {error_details}",
                        extra={"agent": "planner", "phase": "validation"}
                    )
                    
                    retry_message = (
                        "**Output Validation Error**\n\n"
                        "Your response did not match the required PlannerOutput schema.\n\n"
                        f"**Validation errors:**\n```\n{error_details}\n```\n\n"
                        "Please return a JSON object with these required fields:\n"
                        "- `meta`: Object with primary_goal, notable_segments, visual_count, kpi_count, has_time_series, complexity\n"
                        "- `summary`: Brief textual summary of the dashboard plan\n\n"
                        "Optional fields: `needs_additional_analysis`, `needs_user_clarification`"
                    )
                    return types.Content(
                        role="model",
                        parts=[types.Part(text=retry_message)]
                    )
            
            # If it's a string (plain text response), prompt for retry
            elif isinstance(output, str):
                logger.warning(
                    "Planner returned plain text instead of structured output",
                    extra={"agent": "planner", "phase": "validation"}
                )
                
                retry_message = (
                    "**Output Format Error**\n\n"
                    "You returned a plain text response, but this agent requires structured JSON output.\n\n"
                    "Please return a JSON object with these fields:\n"
                    "- `meta`: Object with primary_goal, notable_segments, visual_count, kpi_count, has_time_series, complexity\n"
                    "- `summary`: Brief textual summary of the dashboard plan\n\n"
                    "Optional fields: `needs_additional_analysis`, `needs_user_clarification`"
                )
                return types.Content(
                    role="model",
                    parts=[types.Part(text=retry_message)]
                )
        
        return None
        
    except Exception as e:
        logger.exception(
            f"Error in planner output validation callback: {e}",
            extra={"agent": "planner", "phase": "validation"}
        )
        return None


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
            summarize_actions_tool,
        ],
        include_contents='none',
        output_key=OUTPUT_KEY,
        output_schema=PlannerOutput,
        after_agent_callback=handle_planner_output_validation,
        description="Designs dashboard concepts based on data analysis artifacts.",
    )

    return agent
