"""
Dashboard Orchestrator Agent

This agent serves as the user-facing coordinator for the multi-agent dashboard building system.
It is wrapped by the ManagerAgent which handles the actual delegation to sub-agents.

The Orchestrator:
- Collects user goals and validates data availability
- Calls delegation tools (delegate_data_analysis, delegate_planner)
- The Manager intercepts these calls and routes to the appropriate sub-agent
- Handles follow-up questions and multi-round iterations
- Provides clear user-facing summaries

State Management:
- Uses shared session state with these keys:
  * run_id: Unique identifier for this dashboard building run
  * run_dir: Local directory path for all artifacts
  * data_analysis_output: Structured output from Data Analysis Agent
  * planner_output: Structured output from Planner Agent
  * user_goals: Dictionary containing goal, audience, use_case, constraints
  * dataset_path: Path to the uploaded dataset file
  * data_analysis_summaries: List of action summaries from Data Analysis Agent
  * planner_summaries: List of action summaries from Planner Agent
"""

from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from phoenix.otel import register as register_phoenix

from src.agents.manager.state import STATE_KEY_DATA_ANALYSIS_OUTPUT, STATE_KEY_PLANNER_OUTPUT, STATE_KEY_RUN_ID

from .prompts import build_orchestrator_agent_prompt
from src.core.logging import get_logger
from src.tools.orchestrator import (
    validate_dataset_tool,
    read_state_tool,
    write_user_goals_tool,
)
from src.tools.delegation import (
    delegate_data_analysis_tool,
    delegate_planner_tool,
)

OUTPUT_KEY = "orchestrator_output"

tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)

logger = get_logger(__name__)


def remove_for_context_messages(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """
    Removes "For context: ... [AgentX] said: ..." messages from the LLM request.
    
    These messages are added by ADK for multi-agent context sharing but can
    bloat the context window. Filtering them out reduces token usage.
    
    Args:
        callback_context: ADK callback context
        llm_request: The LLM request to modify (mutated in place)
        
    Returns:
        None to allow normal execution, or LlmResponse to short-circuit
    """
    if llm_request.contents:
        llm_request.contents = [
            c for c in llm_request.contents
            if not (c.parts and c.parts[0].text and c.parts[0].text.startswith("For context:"))
        ]
    return None  # Allow normal execution


def create_orchestrator_agent() -> LlmAgent:
    """
    Create the Dashboard Orchestrator Agent.
    
    This agent:
    1. Collects user goals and validates data availability
    2. Calls delegate_data_analysis to invoke the Data Analysis Agent
    3. Calls delegate_planner to invoke the Planner Agent
    4. Handles follow-up questions and iterations
    5. Returns a synthesized summary with structured outputs
    
    The delegation tools are intercepted by the ManagerAgent which
    routes to the appropriate sub-agent and returns their output.
    
    Returns:
        LlmAgent: Configured orchestrator agent
    """
    model = LiteLlm(model="gpt-5-mini")
    
    agent = LlmAgent(
        name="orchestrator_agent",
        model=model,
        instruction=build_orchestrator_agent_prompt(),
        tools=[
            # State management tools
            validate_dataset_tool,
            read_state_tool,
            write_user_goals_tool,
            # Delegation tools (intercepted by Manager)
            delegate_data_analysis_tool,
            delegate_planner_tool,
        ],
        before_model_callback=remove_for_context_messages,
        after_agent_callback=finalize_orchestrator_response,
        output_key=OUTPUT_KEY,
        description=(
            "User-facing orchestrator agent that coordinates dashboard building "
            "by delegating to Data Analysis and Planner agents."
        ),
    )

    return agent



def finalize_orchestrator_response(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Finalize the orchestrator response after agent completes.
    
    This callback can:
    - Log final state
    - Format structured outputs
    - Check for errors and format user-friendly messages
    - Trigger cleanup operations
    
    Args:
        callback_context: ADK callback context with session state
        
    Returns:
        Optional content to replace agent response (None preserves original)
    """
    try:
        state = callback_context.state
        
        # Log completion
        run_id = state.get(STATE_KEY_RUN_ID, "unknown")
        logger.info(f"Completed run: {run_id}", extra={"agent": "orchestrator", "phase": "finalize", "run_id": run_id})
        
        # Check if we have both outputs
        has_data_analysis = STATE_KEY_DATA_ANALYSIS_OUTPUT in state
        has_planner = STATE_KEY_PLANNER_OUTPUT in state
        
        # Validate structured outputs if present
        error_messages = []
        
        if has_data_analysis:
            data_output = state[STATE_KEY_DATA_ANALYSIS_OUTPUT]
            if not isinstance(data_output, dict):
                error_messages.append(
                    f"Data Analysis Agent returned invalid output type: {type(data_output).__name__} (expected dict)"
                )
            elif not data_output.get("success", False):
                error_messages.append(
                    f"Data Analysis Agent reported failure. Questions: {data_output.get('additional_questions', 'none')}"
                )
        
        if has_planner:
            planner_output = state[STATE_KEY_PLANNER_OUTPUT]
            if not isinstance(planner_output, dict):
                error_messages.append(
                    f"Planner Agent returned invalid output type: {type(planner_output).__name__} (expected dict)"
                )
            elif not planner_output.get("dashboard_spec_path"):
                error_messages.append(
                    "Planner Agent did not create dashboard specification file"
                )
        
        # Log flow progress
        if has_data_analysis and has_planner and not error_messages:
            logger.info("Successfully completed full flow (data analysis → planner)", extra={"agent": "orchestrator", "phase": "finalize", "run_id": run_id})
        elif has_data_analysis and not has_planner:
            logger.info("Data analysis complete, planner not yet invoked", extra={"agent": "orchestrator", "phase": "finalize", "run_id": run_id})
        elif error_messages:
            logger.warning(f"Completed with errors: {'; '.join(error_messages)}", extra={"agent": "orchestrator", "phase": "finalize", "run_id": run_id})
        else:
            logger.info("Still in initial phase", extra={"agent": "orchestrator", "phase": "finalize", "run_id": run_id})
        
        # Return error content if validation failed
        if error_messages:
            error_text = "**Dashboard Building Errors:**\n\n" + "\n".join(f"- {msg}" for msg in error_messages)
            error_text += "\n\nPlease review the agent outputs and try again."
            return types.Content(
                role="model",
                parts=[types.Part(text=error_text)]
            )
        
        # Preserve the original agent response
        return None
        
    except Exception as e:
        error_msg = f"[Orchestrator Error] Failed to finalize response: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, extra={"agent": "orchestrator", "phase": "finalize"})
        return types.Content(
            role="model",
            parts=[types.Part(text=error_msg)]
        )
