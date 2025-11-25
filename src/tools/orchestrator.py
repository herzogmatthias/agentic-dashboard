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
        
        return {
            "valid": True,
            "message": f"Dataset validated successfully: {path.name} ({file_size_mb:.2f} MB)",
            "file_size_mb": round(file_size_mb, 2)
        }
        
    except Exception as e:
        return {
            "valid": False,
            "message": f"Error validating dataset: {str(e)}",
            "file_size_mb": 0
        }


def prepare_data_analysis(
    instructions: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Prepare to delegate to the Data Analysis Agent.
    
    This tool validates prerequisites and stores instructions for the sub-agent.
    After calling this tool, use transfer_to_agent(agent_name='data_analysis_agent')
    to actually invoke the agent.
    
    The Data Analysis Agent will:
    - Profile the dataset
    - Clean the data
    - Generate data_profile.md and cleaning_summary.md
    - Optionally perform additional analyses
    
    Args:
        instructions: Detailed instructions for the Data Analysis Agent.
                     Should include context about what analysis is needed.
        
    Returns:
        Dictionary with:
        - ready: bool indicating if ready to transfer
        - message: str explaining status or next steps
    """
    # Verify prerequisites
    state = tool_context.state
    run_dir = state.get("run_dir")
    dataset_path = state.get("dataset_path")
    
    if not run_dir:
        return {
            "ready": False,
            "message": "No run_dir in state - orchestrator initialization may have failed"
        }
    
    if not dataset_path:
        return {
            "ready": False,
            "message": "No dataset_path in state - please validate dataset first using validate_dataset tool"
        }
    
    # Store the instructions in temp state for the data analysis agent to read
    state["temp:data_analysis_instructions"] = instructions
    
    return {
        "ready": True,
        "message": (
            f"Ready to invoke Data Analysis Agent. "
            f"Use transfer_to_agent(agent_name='data_analysis_agent') to delegate. "
            f"The agent will automatically access the dataset at {dataset_path}"
        )
    }


def prepare_planner(
    handoff_message: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Prepare to delegate to the Planner Agent.
    
    This tool validates prerequisites and stores the handoff message for the sub-agent.
    After calling this tool, use transfer_to_agent(agent_name='planner_agent')
    to actually invoke the agent.
    
    The handoff message should include:
    - User goals (goal, audience, use_case, constraints)
    - Paths to data_profile.md and cleaning_summary.md
    - Paths to any additional analysis artifacts
    
    Args:
        handoff_message: Complete handoff message for the Planner Agent
        
    Returns:
        Dictionary with:
        - ready: bool indicating if ready to transfer
        - message: str explaining status or next steps
    """
    # Verify data analysis has been completed
    state = tool_context.state
    
    if "data_analysis_output" not in state:
        return {
            "ready": False,
            "message": "Data analysis must be completed before planning. Invoke data_analysis_agent first."
        }
    
    # Store the handoff message in temp state for the planner to read
    state["temp:planner_handoff"] = handoff_message
    
    return {
        "ready": True,
        "message": (
            f"Ready to invoke Planner Agent. "
            f"Use transfer_to_agent(agent_name='planner_agent') to delegate. "
            f"The handoff message has been stored for the planner to access."
        )
    }


# Create ADK FunctionTool instances
validate_dataset_tool = FunctionTool(func=validate_dataset)

prepare_data_analysis_tool = FunctionTool(func=prepare_data_analysis)

prepare_planner_tool = FunctionTool(func=prepare_planner)


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
    
    Args:
        key: The state key to read
        
    Returns:
        Dictionary with:
        - found: bool indicating if key exists
        - value: The value (if found)
        - message: Status message
    """
    allowed_keys = {"user_goals", "dataset_path", "data_analysis_output", "planner_output"}
    
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
