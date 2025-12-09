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

# Loop-specific state keys (injected by Loop before Dev invocation)
STATE_KEY_CURRENT_ARTIFACT = "current_artifact"  # The artifact being processed (full dict) - DEPRECATED
STATE_KEY_CURRENT_ARTIFACT_ID = "current_artifact_id"  # Just the ID for quick access - DEPRECATED
STATE_KEY_CURRENT_GROUP = "current_group"  # The group being processed (full dict with artifacts)
STATE_KEY_ACCESSIBLE_FILES = "accessible_files"  # List of file paths accessible to Dev Agent

# Loop result keys (set by Dev agent, read by Loop after artifact completes)
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
    
    Called by the Loop before invoking Dev Agent on each artifact.
    
    Args:
        state: Session state dict
        artifact: The artifact to process
    """
    clear_loop_state(state)
    state[STATE_KEY_CURRENT_ARTIFACT] = artifact
    state[STATE_KEY_CURRENT_ARTIFACT_ID] = artifact.get("id")
    state[STATE_KEY_LOOP_ITERATION] = 0
    state[STATE_KEY_RETRY_COUNT] = 0  # Initialize retry counter


def build_accessible_files_list(artifact: dict[str, Any], run_dir: str | None) -> list[str]:
    """
    Build list of file paths accessible to Dev Agent for this artifact.
    
    Dynamically scans the sample-dashboard project to list existing files in:
    - src/app/api/** (existing API routes)
    - src/models/** (existing TypeScript models)
    - src/lib/** (existing utilities/helpers)
    - data/** (data files)
    
    Also includes run-directory artifacts:
    - backend_manifest.json (from prior artifacts)
    - data_profile.json (from data analysis)
    
    This helps the Dev Agent understand what's already implemented.
    
    Args:
        artifact: The artifact being processed
        run_dir: Path to run directory (may be None)
        
    Returns:
        List of accessible file paths (absolute or relative)
    """
    from pathlib import Path
    
    paths: list[str] = []
    
    # Get sample-dashboard root
    # From tools.py: go up 5 levels to reach Documents/agentic-dashboard/, then into sample-dashboard/
    sample_dashboard_root = Path(__file__).parent.parent.parent.parent.parent / "sample-dashboard"
    
    try:
        # Scan src/app/api for existing routes
        api_dir = sample_dashboard_root / "src" / "app" / "api"
        if api_dir.exists():
            for route_file in api_dir.rglob("route.ts"):
                paths.append(str(route_file.relative_to(sample_dashboard_root)))
            logger.debug(f"Found {len([p for p in paths if 'api' in p])} API routes")
    except Exception as e:
        logger.debug(f"Error scanning API directory: {e}")
    
    try:
        # Scan src/models for existing TypeScript models
        models_dir = sample_dashboard_root / "src" / "models"
        if models_dir.exists():
            for model_file in models_dir.glob("*.ts"):
                paths.append(str(model_file.relative_to(sample_dashboard_root)))
            logger.debug(f"Found {len([p for p in paths if 'models' in p])} model files")
    except Exception as e:
        logger.debug(f"Error scanning models directory: {e}")
    
    try:
        # Scan src/lib for existing utilities
        lib_dir = sample_dashboard_root / "src" / "lib"
        if lib_dir.exists():
            for util_file in lib_dir.rglob("*.ts"):
                paths.append(str(util_file.relative_to(sample_dashboard_root)))
            logger.debug(f"Found {len([p for p in paths if 'lib' in p])} utility files")
    except Exception as e:
        logger.debug(f"Error scanning lib directory: {e}")
    
    try:
        # Scan data directory for CSV and other data files
        data_dir = sample_dashboard_root / "data"
        if data_dir.exists():
            for data_file in data_dir.glob("*"):
                if data_file.is_file():
                    paths.append(str(data_file.relative_to(sample_dashboard_root)))
            logger.debug(f"Found {len([p for p in paths if 'data' in p])} data files")
    except Exception as e:
        logger.debug(f"Error scanning data directory: {e}")

    
    logger.info(
        f"Built accessible files list with {len(paths)} files",
        extra={"accessible_file_count": len(paths), "artifact_id": artifact.get("id")}
    )
    
    return paths
