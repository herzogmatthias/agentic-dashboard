"""
Orchestrator tools for sub-agent coordination and state management.

These tools allow the orchestrator agent to:
- Validate dataset availability
- Prepare for Data Analysis Agent delegation  
- Prepare for Planner Agent delegation
- Read session state (user_goals, dataset_path, data_analysis_output, planner_output)
- Write user_goals to session state

Note: Actual sub-agent invocation happens via ADK's transfer_to_agent mechanism.
Sub-agents share the same session state and invocation context.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from google.adk.tools import FunctionTool, ToolContext
from src.core.logging import get_logger

logger = get_logger(__name__)


def validate_dataset(
    dataset_path: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Validate that a dataset file exists and is accessible.
    
    This tool checks:
    - File exists
    - File is readable
    - File has a supported extension (.csv, .parquet, .json)
    - File is not empty
    
    Args:
        dataset_path: Path to the dataset file to validate
        
    Returns:
        Dictionary with validation results:
        - valid: bool indicating if dataset is valid
        - message: str with validation result or error details
        - file_size_mb: float indicating file size in MB (if valid)
    """
    try:
        path = Path(dataset_path).resolve()
        
        # Check if file exists
        if not path.exists():
            return {
                "valid": False,
                "message": f"Dataset file not found: {dataset_path}",
                "file_size_mb": 0
            }
        
        # Check if it's a file (not a directory)
        if not path.is_file():
            return {
                "valid": False,
                "message": f"Path is not a file: {dataset_path}",
                "file_size_mb": 0
            }
        
        # Check supported extensions
        supported_extensions = {".csv", ".parquet", ".json", ".xlsx"}
        if path.suffix.lower() not in supported_extensions:
            return {
                "valid": False,
                "message": f"Unsupported file type: {path.suffix}. Supported: {supported_extensions}",
                "file_size_mb": 0
            }
        
        # Check file size
        file_size_bytes = path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_bytes == 0:
            return {
                "valid": False,
                "message": "Dataset file is empty",
                "file_size_mb": 0
            }
        
        # Update state with validated dataset path
        tool_context.state["dataset_path"] = str(path)
        logger.info(
            "Dataset validated",
            extra={"agent": "orchestrator", "phase": "validate_dataset", "dataset": str(path), "file_size_mb": round(file_size_mb, 2)},
        )
        
        return {
            "valid": True,
            "message": f"Dataset validated successfully: {path.name} ({file_size_mb:.2f} MB)",
            "file_size_mb": round(file_size_mb, 2)
        }
        
    except Exception as e:
        logger.exception("Dataset validation error", extra={"agent": "orchestrator", "phase": "validate_dataset"})
        return {
            "valid": False,
            "message": f"Error validating dataset: {str(e)}",
            "file_size_mb": 0
        }


# Create ADK FunctionTool instances
validate_dataset_tool = FunctionTool(func=validate_dataset)



# State management tools

def read_state(
    key: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Read a value from session state.
    
    Available keys (read-only for orchestrator):
    - user_goals: Dictionary with goal, audience, use_case, constraints
    - dataset_path: Path to uploaded dataset
    - data_analysis_output: Structured output from Data Analysis Agent
    - planner_output: Structured output from Planner Agent
    - additional_artifacts_path: List of additional analysis artifacts produced
    - dashboard_spec_path: Path to dashboard JSON specification
    
    Args:
        key: The state key to read
        
    Returns:
        Dictionary with:
        - found: bool indicating if key exists
        - value: The value (if found)
        - message: Status message
    """
    allowed_keys = {"user_goals", "dataset_path", "data_analysis_output", "planner_output", "additional_artifacts_path", "dashboard_spec_path"}
    
    if key not in allowed_keys:
        return {
            "found": False,
            "value": None,
            "message": f"Key '{key}' not allowed. Allowed keys: {allowed_keys}"
        }
    
    state = tool_context.state
    
    if key not in state:
        return {
            "found": False,
            "value": None,
            "message": f"Key '{key}' not found in state. It may not have been set yet."
        }
    
    return {
        "found": True,
        "value": state[key],
        "message": f"Successfully retrieved '{key}' from state"
    }


def write_user_goals(
    goal: str,
    audience: str,
    use_case: str,
    constraints: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Write user goals to session state.
    
    This is the ONLY state key the orchestrator can write to.
    All other state updates are handled automatically by sub-agents and callbacks.
    
    Args:
        goal: High-level purpose of the dashboard
        audience: Target audience (e.g., "managers", "analysts")
        use_case: Primary use case (e.g., "monitoring", "exploration", "reporting")
        constraints: Comma-separated list of constraints or "none"
        
    Returns:
        Dictionary with:
        - success: bool indicating if write succeeded
        - message: Status message
    """
    # Parse constraints
    constraints_list = []
    if constraints and constraints.lower() != "none":
        constraints_list = [c.strip() for c in constraints.split(",") if c.strip()]
    
    user_goals = {
        "goal": goal,
        "audience": audience,
        "use_case": use_case,
        "constraints": constraints_list
    }
    
    tool_context.state["user_goals"] = user_goals
    
    return {
        "success": True,
        "message": f"User goals saved to state: {user_goals}"
    }


read_state_tool = FunctionTool(func=read_state)

write_user_goals_tool = FunctionTool(func=write_user_goals)
