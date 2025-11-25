"""
Orchestrator tools for sub-agent invocation and coordination.

These tools allow the orchestrator agent to:
- Validate dataset availability
- Invoke the Data Analysis Agent
- Invoke the Planner Agent
- Manage the dashboard building workflow
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from google.adk.tools import FunctionTool, ToolContext
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from src.agents.data_analysis.agent import create_data_analysis_agent
from src.agents.planner.agent import create_planner_agent
from src.core.config import APP_NAME, USER_ID


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
        tool_context: ADK tool context with session state
        
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
        state = tool_context.invocation_context.session.state
        state["dataset_path"] = str(path)
        
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


def invoke_data_analysis_agent(
    instructions: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Invoke the Data Analysis Agent with specific instructions.
    
    This tool creates a new sub-session for the Data Analysis Agent,
    sends it the provided instructions, and waits for completion.
    
    The agent will:
    - Profile the dataset
    - Clean the data
    - Generate data_profile.md and cleaning_summary.md
    - Optionally perform additional analyses
    
    Args:
        instructions: Detailed instructions for the Data Analysis Agent.
                     Should include context about what analysis is needed.
        tool_context: ADK tool context with session state
        
    Returns:
        Dictionary with:
        - success: bool indicating if agent completed successfully
        - output: Dict containing the structured DataAnalysisOutput
        - message: str with summary of what happened
    """
    try:
        # Get current state
        state = tool_context.invocation_context.session.state
        run_dir = state.get("run_dir")
        dataset_path = state.get("dataset_path")
        
        if not run_dir:
            return {
                "success": False,
                "output": None,
                "message": "No run_dir in state - orchestrator initialization may have failed"
            }
        
        if not dataset_path:
            return {
                "success": False,
                "output": None,
                "message": "No dataset_path in state - please validate dataset first"
            }
        
        # Create Data Analysis Agent
        agent = create_data_analysis_agent()
        runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
        
        # Create a sub-session for the data analysis agent
        # Note: The sub-agent will inherit run_dir and run_id from state
        async def run_agent():
            session = await runner.session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                state=state  # Pass current state to sub-agent
            )
            
            # Send instructions to agent
            user_content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=instructions)]
            )
            
            final_response = None
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=session.id,
                new_message=user_content,
            ):
                if event.is_final_response() and event.content:
                    final_response = event.content
            
            # Get the output from session state
            output = session.state.get("data_analysis_output")
            
            return output, final_response
        
        # Run the agent
        output, final_response = asyncio.run(run_agent())
        
        if not output:
            return {
                "success": False,
                "output": None,
                "message": "Data Analysis Agent did not produce structured output"
            }
        
        # Update orchestrator state with the output
        state["data_analysis_output"] = output
        
        return {
            "success": output.get("success", False),
            "output": output,
            "message": f"Data Analysis Agent completed. Success: {output.get('success', False)}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "message": f"Error invoking Data Analysis Agent: {str(e)}"
        }


def invoke_planner_agent(
    handoff_message: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Invoke the Planner Agent with a handoff message containing data context.
    
    The handoff message should include:
    - User goals (goal, audience, use_case, constraints)
    - Paths to data_profile.md and cleaning_summary.md
    - Paths to any additional analysis artifacts
    
    Args:
        handoff_message: Complete handoff message for the Planner Agent
        tool_context: ADK tool context with session state
        
    Returns:
        Dictionary with:
        - success: bool indicating if planner completed successfully
        - output: Dict containing the structured PlannerOutput
        - message: str with summary of what happened
    """
    try:
        # Get current state
        state = tool_context.invocation_context.session.state
        
        # Verify data analysis has been completed
        if "data_analysis_output" not in state:
            return {
                "success": False,
                "output": None,
                "message": "Data analysis must be completed before planning"
            }
        
        # Create Planner Agent
        agent = create_planner_agent()
        runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
        
        # Create a sub-session for the planner agent
        async def run_agent():
            session = await runner.session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                state=state  # Pass current state to sub-agent
            )
            
            # Send handoff message to planner
            user_content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=handoff_message)]
            )
            
            final_response = None
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=session.id,
                new_message=user_content,
            ):
                if event.is_final_response() and event.content:
                    final_response = event.content
            
            # Get the output from session state
            output = session.state.get("planner_output")
            
            return output, final_response
        
        # Run the agent
        output, final_response = asyncio.run(run_agent())
        
        if not output:
            return {
                "success": False,
                "output": None,
                "message": "Planner Agent did not produce structured output"
            }
        
        # Update orchestrator state with the output
        state["planner_output"] = output
        
        return {
            "success": True,
            "output": output,
            "message": "Planner Agent completed successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "message": f"Error invoking Planner Agent: {str(e)}"
        }


# Create ADK FunctionTool instances
validate_dataset_tool = FunctionTool(func=validate_dataset)

invoke_data_analysis_agent_tool = FunctionTool(func=invoke_data_analysis_agent)

invoke_planner_agent_tool = FunctionTool(func=invoke_planner_agent)

