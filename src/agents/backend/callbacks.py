"""
Backend Agent callbacks.

Callback functions for state initialization, context injection, and response handling.
"""

from pathlib import Path

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as gt

from src.core.logging import get_logger
from src.agents.utils import load_context_for_backend
from src.agents.backend.utils import get_cleaned_data_files
from src.agents.backend.prompts import build_backend_agent_prompt
from src.tools.backend import copy_data_to_project, SAMPLE_DASHBOARD_ROOT

logger = get_logger(__name__)

# State keys
STATE_KEY_RUN_ID = "run_id"
STATE_KEY_RUN_DIR = "run_dir"
STATE_KEY_DATA_PROFILE_PATH = "data_profile_path"
STATE_KEY_DASHBOARD_SPEC_PATH = "dashboard_spec_path"
STATE_KEY_CLEANED_DATA_FILES = "cleaned_data_files"
STATE_KEY_CLEANED_DATA_PATH = "cleaned_data_path"
STATE_KEY_CONTINUATION_COUNT = "_backend_continuation_count"

# Default run directory for standalone testing
DEFAULT_TEST_RUN_DIR = Path("runs/run_20251204_142914")

# Maximum number of continuation attempts
MAX_CONTINUATION_ATTEMPTS = 3


def inject_context_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """
    Before-model callback that injects context artifacts into the LLM request.
    
    This callback reads the JSON artifacts from the run directory and injects them as a
    user message for context. Continuation handling is done by BackendAgentWithContinuation.
    
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
            logger.debug("No run_dir in state, skipping context injection", extra={"agent": "backend"})
            return None
        
        # Load context from artifacts (minified, not truncated)
        context = load_context_for_backend(run_dir)
        
        if not context:
            logger.debug("No context loaded, skipping injection", extra={"agent": "backend"})
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
            "Injected context into backend request",
            extra={
                "agent": "backend",
                "has_dashboard": "dashboard_concept" in context,
                "has_profile": "data_profile" in context,
                "has_metrics": "metrics_summary" in context,
                "insert_position": insert_pos,
            }
        )
        
    except Exception as e:
        logger.warning(
            f"Failed to inject context: {e}",
            extra={"agent": "backend", "error": str(e)}
        )
    
    return None


def initialize_backend_state(callback_context: CallbackContext) -> gt.Content | None:
    """
    Initialize session state for the Backend Agent.
    
    This callback:
    1. Sets up run_id and run_dir if not present
    2. Sets data_profile_path and dashboard_spec_path
    3. Copies cleaned data files to sample-dashboard/data/
    4. Populates cleaned_data_files list
    
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
                f"Backend agent using default test run: {run_dir}",
                extra={"agent": "backend", "phase": "init", "run_id": DEFAULT_TEST_RUN_DIR.name}
            )
        else:
            run_dir = Path(state[STATE_KEY_RUN_DIR])
        
        # Set data_profile_path if not present
        if STATE_KEY_DATA_PROFILE_PATH not in state or state[STATE_KEY_DATA_PROFILE_PATH] is None:
            data_profile_path = run_dir / "data_profile.md"
            if data_profile_path.exists():
                state[STATE_KEY_DATA_PROFILE_PATH] = str(data_profile_path.resolve())
        
        # Set dashboard_spec_path if not present
        if STATE_KEY_DASHBOARD_SPEC_PATH not in state or state[STATE_KEY_DASHBOARD_SPEC_PATH] is None:
            dashboard_spec_path = run_dir / "planner" / "dashboard_concept.json"
            if dashboard_spec_path.exists():
                state[STATE_KEY_DASHBOARD_SPEC_PATH] = str(dashboard_spec_path.resolve())
        
        # Copy cleaned data to sample-dashboard/data/
        state_dict = {
            STATE_KEY_RUN_DIR: state.get(STATE_KEY_RUN_DIR),
            STATE_KEY_CLEANED_DATA_PATH: state.get(STATE_KEY_CLEANED_DATA_PATH),
        }
        copy_result = copy_data_to_project(state_dict)
        if "error" in copy_result:
            logger.warning(
                f"Failed to copy data to project: {copy_result['error']}",
                extra={"agent": "backend", "phase": "init"}
            )
        else:
            logger.info(
                f"Copied {copy_result.get('total_files', 0)} files to sample-dashboard/data/",
                extra={"agent": "backend", "phase": "init", "files": copy_result.get('total_files', 0)}
            )
        
        # Populate cleaned_data_files list
        cleaned_files = get_cleaned_data_files(run_dir)
        state[STATE_KEY_CLEANED_DATA_FILES] = cleaned_files
        
        # Initialize continuation count
        state[STATE_KEY_CONTINUATION_COUNT] = 0
        
        logger.info(
            f"Backend agent state initialized",
            extra={
                "agent": "backend",
                "phase": "init",
                "run_dir": str(run_dir),
                "cleaned_files_count": len(cleaned_files),
            }
        )
        
    except Exception as e:
        logger.exception(
            f"Failed to initialize backend state: {e}",
            extra={"agent": "backend", "phase": "init"}
        )
    
    return None


async def backend_instruction_provider(context: ReadonlyContext) -> str:
    """
    Dynamic instruction provider that injects session state into the prompt.
    
    Args:
        context: ReadonlyContext with access to session state
        
    Returns:
        Prompt string with state values injected
    """
    from src.agents.backend.utils import format_cleaned_files_for_prompt
    
    state = context.state
    
    # Get cleaned files from state
    cleaned_files = state.get(STATE_KEY_CLEANED_DATA_FILES, [])
    cleaned_data_files = format_cleaned_files_for_prompt(cleaned_files)
    
    # Get project root as absolute path
    project_root = str(SAMPLE_DASHBOARD_ROOT.resolve())
    
    return build_backend_agent_prompt(
        cleaned_data_files=cleaned_data_files,
        project_root=project_root,
    )
