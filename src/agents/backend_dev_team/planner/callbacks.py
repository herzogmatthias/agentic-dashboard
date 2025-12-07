"""
Backend Planner Agent callbacks.

Callback functions for state initialization and context injection.
"""

from pathlib import Path

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as gt

from src.core.logging import get_logger
from src.agents.utils import load_context_for_backend
from src.agents.backend_dev_team.planner.prompts import build_backend_planner_prompt

logger = get_logger(__name__)

# State keys
STATE_KEY_RUN_ID = "run_id"
STATE_KEY_RUN_DIR = "run_dir"
STATE_KEY_BACKEND_TODO_LIST = "backend_todo_list"
STATE_KEY_BACKEND_TODOS_PATH = "backend_todos_path"

# Default run directory for standalone testing
DEFAULT_TEST_RUN_DIR = Path("runs/run_20251204_142914")


def inject_planner_context_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """
    Before-model callback that injects context artifacts into the LLM request.
    
    This callback reads the JSON artifacts from the run directory and injects them as a
    user message for context. The planner needs dashboard_concept, data_profile, and
    metrics_summary to create the artifact todo list.
    
    Args:
        callback_context: The callback context with state access
        llm_request: The LLM request to modify
        
    Returns:
        None to continue with modified request
    """
    try:
        state = callback_context.state
        run_dir = state.get(STATE_KEY_RUN_DIR)
        
        if not run_dir:
            logger.debug(
                "No run_dir in state, skipping context injection",
                extra={"agent": "backend_planner"}
            )
            return None
        
        # Load context from artifacts (minified, not truncated)
        context = load_context_for_backend(run_dir)
        
        if not context:
            logger.debug(
                "No context loaded, skipping injection",
                extra={"agent": "backend_planner"}
            )
            return None
        
        # Build context message parts
        parts = []
        
        if "dashboard_concept" in context:
            parts.append(f"=== DASHBOARD CONCEPT ===\n{context['dashboard_concept']}")
        elif "dashboard_concept_error" in context:
            parts.append(f"=== DASHBOARD CONCEPT ERROR ===\n{context['dashboard_concept_error']}")
        
        if "data_profile" in context:
            parts.append(f"=== DATA PROFILE ===\n{context['data_profile']}")
        elif "data_profile_error" in context:
            parts.append(f"=== DATA PROFILE ERROR ===\n{context['data_profile_error']}")
        
        if "metrics_summary" in context:
            parts.append(f"=== METRICS SUMMARY ===\n{context['metrics_summary']}")
        elif "metrics_summary_error" in context:
            parts.append(f"=== METRICS SUMMARY ERROR ===\n{context['metrics_summary_error']}")
        
        if not parts:
            return None
        
        # Create context message
        context_text = "For context (auto-injected artifacts):\n\n" + "\n\n".join(parts)
        context_message = gt.Content(
            role="user",
            parts=[gt.Part.from_text(text=context_text)],
        )
        
        # Insert after first user message (index 1) rather than appending to end
        if llm_request.contents is None:
            llm_request.contents = []
        
        # Find position after first user message
        insert_pos = 1
        for i, content in enumerate(llm_request.contents):
            if content.role == "user":
                insert_pos = i + 1
                break
        
        # Insert at the calculated position
        llm_request.contents.insert(insert_pos, context_message)
        
        logger.info(
            "Injected context into backend planner request",
            extra={
                "agent": "backend_planner",
                "has_dashboard": "dashboard_concept" in context,
                "has_profile": "data_profile" in context,
                "has_metrics": "metrics_summary" in context,
                "insert_position": insert_pos,
            }
        )
        
    except Exception as e:
        logger.warning(
            f"Failed to inject context: {e}",
            extra={"agent": "backend_planner", "error": str(e)}
        )
    
    return None


def initialize_planner_state(callback_context: CallbackContext) -> gt.Content | None:
    """
    Initialize session state for the Backend Planner Agent.
    
    This callback:
    1. Sets up run_id and run_dir if not present
    2. Initializes backend_todo_list state key
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        None to allow normal agent execution
    """
    try:
        state = callback_context.state
        
        # Use existing run_dir or default for standalone testing
        if STATE_KEY_RUN_DIR not in state or state[STATE_KEY_RUN_DIR] is None:
            run_dir = DEFAULT_TEST_RUN_DIR.resolve()
            state[STATE_KEY_RUN_DIR] = str(run_dir)
            state[STATE_KEY_RUN_ID] = DEFAULT_TEST_RUN_DIR.name
            logger.info(
                f"Backend planner using default test run: {run_dir}",
                extra={
                    "agent": "backend_planner",
                    "phase": "init",
                    "run_id": DEFAULT_TEST_RUN_DIR.name
                }
            )
        else:
            run_dir = Path(state[STATE_KEY_RUN_DIR])
        
        # Initialize todo list state if not present
        if STATE_KEY_BACKEND_TODO_LIST not in state:
            state[STATE_KEY_BACKEND_TODO_LIST] = None
        
        logger.info(
            "Backend planner state initialized",
            extra={
                "agent": "backend_planner",
                "phase": "init",
                "run_dir": str(run_dir),
            }
        )
        
    except Exception as e:
        logger.exception(
            f"Failed to initialize backend planner state: {e}",
            extra={"agent": "backend_planner", "phase": "init"}
        )
    
    return None


async def planner_instruction_provider(context: ReadonlyContext) -> str:
    """
    Dynamic instruction provider for the Backend Planner Agent.
    
    Args:
        context: ReadonlyContext with access to session state
        
    Returns:
        Prompt string
    """
    return build_backend_planner_prompt()
