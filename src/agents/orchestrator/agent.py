"""
Dashboard Orchestrator Agent

This agent serves as the root entry point for the multi-agent dashboard building system.
It coordinates the Data Analysis Agent and Planner Agent following the flow:
  
  User → Orchestrator → Data Analysis Agent → Orchestrator → Planner Agent → Orchestrator → User

Architecture Decision:
- Implementation: Single LlmAgent with tools to invoke sub-agents
- Rationale: Provides flexibility for:
  * Dynamic goal collection and data validation
  * Conditional sub-agent invocation based on context
  * Custom handoff message construction
  * Handling follow-up questions and multi-round iterations
  * Clear separation between user-facing and agent-facing communication

State Management:
- Uses shared session state with these keys:
  * run_id: Unique identifier for this dashboard building run
  * run_dir: Local directory path for all artifacts
  * data_analysis_output: Structured output from Data Analysis Agent
  * planner_output: Structured output from Planner Agent
  * user_goals: Dictionary containing goal, audience, use_case, constraints
  * dataset_path: Path to the uploaded dataset file

Execution Limits and Error Handling:
- Timeout Strategy (v1): Relies on LLM API timeouts (typically 60s per request)
    and agent's natural completion behavior. Future: wrap runner.run_async() with
    asyncio.wait_for(timeout=AGENT_TIMEOUT_SECONDS).
- Max Tool Calls: ADK doesn't support native limits. Deferred to testing phase -
    will implement callback-based tracking if infinite loops occur.
- Retry Strategy (v1): Sub-agent failures propagate to orchestrator, which can
    handle via tools or prompt instructions. Future: implement exponential backoff
    retry wrapper around transfer_to_agent() calls.
- Error Reporting: Callbacks check for missing state, parsing errors, and agent
    failures. Format user-friendly messages with phase/agent/reason context.
"""

from pathlib import Path
from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from phoenix.otel import register as register_phoenix

from src.prompts.system_prompts import build_orchestrator_agent_prompt
from src.core.state import _bootstrap_run_directory
from src.tools.orchestrator import (
    validate_dataset_tool,
    prepare_data_analysis_tool,
    prepare_planner_tool,
    read_state_tool,
    write_user_goals_tool,
)
from src.agents.data_analysis.agent import create_data_analysis_agent
from src.agents.planner.agent import create_planner_agent


# State keys used by the orchestrator
STATE_KEY_RUN_ID = "run_id"
STATE_KEY_RUN_DIR = "run_dir"
STATE_KEY_DATA_ANALYSIS_OUTPUT = "data_analysis_output"
STATE_KEY_PLANNER_OUTPUT = "planner_output"
STATE_KEY_USER_GOALS = "user_goals"
STATE_KEY_DATASET_PATH = "dataset_path"

OUTPUT_KEY = "orchestrator_output"


tracer_provider = register_phoenix(
    project_name="default",
    auto_instrument=True,
)


def create_orchestrator_agent() -> LlmAgent:
    """
    Create the Dashboard Orchestrator Agent.
    
    This is the root agent that:
    1. Collects user goals and validates data availability
    2. Invokes the Data Analysis Agent 
    3. Invokes the Planner Agent with appropriate context
    4. Handles follow-up questions and iterations
    5. Returns a synthesized summary with structured outputs
    
    The agent uses tools to delegate to sub-agents and manages
    the overall dashboard building flow.
    
    Returns:
        LlmAgent: Configured orchestrator agent
    """
    model = LiteLlm(model="gpt-4o-mini")

    # Create sub-agents that will be delegated to
    data_analysis_agent = create_data_analysis_agent()
    planner_agent = create_planner_agent()
    
    agent = LlmAgent(
        name="orchestrator_agent",
        model=model,
        instruction=build_orchestrator_agent_prompt(),
        tools=[
            validate_dataset_tool,
            prepare_data_analysis_tool,
            prepare_planner_tool,
            read_state_tool,
            write_user_goals_tool,
        ],
        sub_agents=[
            data_analysis_agent,
            planner_agent,
        ],
        before_agent_callback=initialize_orchestrator_state,
        after_agent_callback=finalize_orchestrator_response,
        output_key=OUTPUT_KEY,
        description=(
            "Root orchestrator agent that coordinates dashboard building "
            "by managing Data Analysis and Planner agents."
        ),
    )

    return agent


def initialize_orchestrator_state(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Initialize orchestrator state before the agent runs.
    
    This is the single point of state initialization for the entire system.
    Creates run_id and run_dir if they don't exist, and sets up all required state keys.
    This callback runs before each agent invocation.
    
    Args:
        callback_context: ADK callback context with session state
        
    Returns:
        Optional content to inject (None means no injection)
    """
    try:
        state = callback_context.state
        
        # Initialize run_id and run_dir if not already present
        # This is the SINGLE SOURCE OF TRUTH for run initialization
        if STATE_KEY_RUN_ID not in state or STATE_KEY_RUN_DIR not in state:
            run_id, run_dir = _bootstrap_run_directory()
            state[STATE_KEY_RUN_ID] = run_id
            state[STATE_KEY_RUN_DIR] = str(run_dir)
            print(f"[Orchestrator] Created new run: {run_id} at {run_dir}")
        else:
            print(f"[Orchestrator] Using existing run: {state.get(STATE_KEY_RUN_ID)}")
        
        # Initialize user_goals if not present
        if STATE_KEY_USER_GOALS not in state:
            state[STATE_KEY_USER_GOALS] = {
                "goal": None,
                "audience": None,
                "use_case": None,
                "constraints": []
            }
        
        # Ensure dataset_path is initialized
        if STATE_KEY_DATASET_PATH not in state:
            state[STATE_KEY_DATASET_PATH] = None
        
        return None
    except Exception as e:
        error_msg = f"[Orchestrator Error] Failed to initialize state: {type(e).__name__}: {str(e)}"
        print(error_msg)
        # Return error content to user
        return types.Content(
            role="model",
            parts=[types.Part(text=error_msg)]
        )


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
        print(f"[Orchestrator] Completed run: {run_id}")
        
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
            print("[Orchestrator] ✅ Successfully completed full flow (data analysis → planner)")
        elif has_data_analysis and not has_planner:
            print("[Orchestrator] Data analysis complete, planner not yet invoked")
        elif error_messages:
            print(f"[Orchestrator] ⚠️ Completed with errors: {'; '.join(error_messages)}")
        else:
            print("[Orchestrator] Still in initial phase")
        
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
        print(error_msg)
        return types.Content(
            role="model",
            parts=[types.Part(text=error_msg)]
        )
