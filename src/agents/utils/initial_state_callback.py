from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from src.core.state import _bootstrap_run_directory

def initial_state(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Inject initial state into the agent's session.

    This function is called when the agent session is created. It can be used to
    set up any necessary state or context for the agent to operate.

    Args:
        context (CallBackContext): The callback context provided by the ADK.
    Returns:
        dict: A dictionary representing the initial state.
    # Example initial state; modify as needed for your application
    initial_state = {
        "user_id": "12345",
        "preferences": {
            "language": "en",
            "timezone": "UTC"
        },
        "session_start_time": context.current_time.isoformat()
    }
    return initial_state
    """
    #Check if state already has run_dir and run_id, if so, return them
    existing_state = callback_context.state or {}
    run_dir = existing_state.get("run_dir")
    run_id = existing_state.get("run_id")
    if run_dir and run_id:
        return None
    # Otherwise, create new run_dir and run_id

    run_id, run_dir = _bootstrap_run_directory()
    callback_context.state["run_id"] = run_id
    callback_context.state["run_dir"] = str(run_dir)
  
    return None