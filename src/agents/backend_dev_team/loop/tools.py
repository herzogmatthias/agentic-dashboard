"""
Loop Agent tools - exit_loop tool for signaling loop termination.

The Loop Agent uses an ADK LoopAgent (deterministic workflow) that cycles
through Dev → Tester → QA sub-agents. This module provides:
1. exit_loop tool - signals the loop to terminate when QA passes
2. State helpers for callbacks to inject artifact context
"""

from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# State keys
# =============================================================================

# Shared with planner
STATE_KEY_RUN_DIR = "run_dir"
STATE_KEY_RUN_ID = "run_id"
STATE_KEY_BACKEND_TODO_LIST = "backend_todo_list"
STATE_KEY_BACKEND_TODOS_PATH = "backend_todos_path"

# Loop-specific state keys (injected by Planner before handoff)
STATE_KEY_CURRENT_ARTIFACT = "current_artifact"  # The artifact being processed (full dict)
STATE_KEY_CURRENT_ARTIFACT_ID = "current_artifact_id"  # Just the ID for quick access

# Loop result keys (set by QA agent, read by Planner after loop returns)
STATE_KEY_LOOP_RESULT = "loop_result"  # "pass" | "fail" | "error"
STATE_KEY_LOOP_ERROR = "loop_error"  # Error message if result is "error"
STATE_KEY_LOOP_ITERATION = "loop_iteration"  # Current iteration count (set by loop)


STATE_KEY_QA_RESULT = "qa_result"  # Dict with validation result

# Report path keys (for persisting reports after loop)
STATE_KEY_DEV_REPORT_PATH = "dev_report_path"  # Path to persisted DevReport
STATE_KEY_TEST_REPORT_PATH = "test_report_path"  # Path to persisted TestReport

# Retry tracking (shared counter across Dev/Test/QA failures)
STATE_KEY_RETRY_COUNT = "retry_count"  # Total retries in current artifact loop

# Previous test summary (passed from Tester to Dev on retry)
STATE_KEY_PREVIOUS_TEST_SUMMARY = "previous_test_summary"

# Escalation state
STATE_KEY_ESCALATION_REASON = "escalation_reason"  # Why we escalated

# Constants
MAX_ITERATIONS = 5  # Max Dev→Tester→QA cycles before giving up
MAX_TOTAL_RETRIES = 5  # Total retries before escalation


# =============================================================================
# Exit Loop Tool
# =============================================================================

def exit_loop(tool_context: ToolContext) -> dict[str, Any]:
    """
    Signal that the loop should terminate.
    
    Call this tool when:
    - QA passes (artifact is done)
    - An unrecoverable error occurs
    - Max iterations reached (handled by LoopAgent automatically)
    
    This sets the escalate flag which tells the ADK LoopAgent to exit.
    
    Args:
        tool_context: ADK tool context
        
    Returns:
        Confirmation message
    """
    agent_name = tool_context.agent_name
    logger.info(
        f"exit_loop triggered by {agent_name}",
        extra={"agent": "loop", "triggered_by": agent_name}
    )
    
    # Set escalate flag to signal loop exit
    tool_context.actions.escalate = True
    
    return {
        "success": True,
        "message": f"Loop exit signaled by {agent_name}",
    }


# FunctionTool wrapper
exit_loop_tool = FunctionTool(exit_loop)


# =============================================================================
# State helper functions (used by callbacks, not as tools)
# =============================================================================

def get_current_artifact(state: dict[str, Any]) -> dict[str, Any] | None:
    """
    Get the current artifact from state.
    
    Args:
        state: Session state dict
        
    Returns:
        The current artifact dict or None
    """
    return state.get(STATE_KEY_CURRENT_ARTIFACT)


def get_loop_result(state: dict[str, Any]) -> str | None:
    """
    Get the loop result from state.
    
    Args:
        state: Session state dict
        
    Returns:
        "pass", "fail", "error", or None if not set
    """
    return state.get(STATE_KEY_LOOP_RESULT)


def set_loop_result(state: dict[str, Any], result: str, error: str | None = None) -> None:
    """
    Set the loop result in state.
    
    Args:
        state: Session state dict
        result: "pass", "fail", or "error"
        error: Error message if result is "error"
    """
    state[STATE_KEY_LOOP_RESULT] = result
    if error:
        state[STATE_KEY_LOOP_ERROR] = error
    elif STATE_KEY_LOOP_ERROR in state:
        del state[STATE_KEY_LOOP_ERROR]


def clear_loop_state(state: dict[str, Any]) -> None:
    """
    Clear loop-specific state keys (called before each new artifact).
    
    Args:
        state: Session state dict
    """
    keys_to_clear = [
        STATE_KEY_CURRENT_ARTIFACT,
        STATE_KEY_CURRENT_ARTIFACT_ID,
        STATE_KEY_LOOP_RESULT,
        STATE_KEY_LOOP_ERROR,
        STATE_KEY_LOOP_ITERATION,
        STATE_KEY_QA_RESULT,
        STATE_KEY_DEV_REPORT_PATH,
        STATE_KEY_TEST_REPORT_PATH,
        STATE_KEY_RETRY_COUNT,
        STATE_KEY_PREVIOUS_TEST_SUMMARY,
        STATE_KEY_ESCALATION_REASON,
    ]
    for key in keys_to_clear:
        if key in state:
            del state[key]


def inject_artifact_to_state(state: dict[str, Any], artifact: dict[str, Any]) -> None:
    """
    Inject an artifact into state for the loop to process.
    
    Called by the Planner before handing off to the Loop.
    
    Args:
        state: Session state dict
        artifact: The artifact to process
    """
    clear_loop_state(state)
    state[STATE_KEY_CURRENT_ARTIFACT] = artifact
    state[STATE_KEY_CURRENT_ARTIFACT_ID] = artifact.get("id")
    state[STATE_KEY_LOOP_ITERATION] = 0
    state[STATE_KEY_RETRY_COUNT] = 0  # Initialize retry counter
