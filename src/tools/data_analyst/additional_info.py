"""
Tools for accessing additional information provided by the user.
"""

from pathlib import Path
from typing import Any, Dict
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.agents.manager.state import STATE_KEY_RUN_DIR
from src.core.logging import get_logger

logger = get_logger(__name__)


def check_for_additional_info(tool_context: ToolContext) -> Dict[str, Any]:
    """
    List all files with additional information supplied by the user.
    
    This tool checks for any user-provided additional context or instructions
    that might help with data analysis (e.g., data dictionaries, domain knowledge,
    column descriptions).
    
    Returns:
        Dictionary containing:
        - files: List of file names found in run_dir/additional_info
        - count: Number of files found
        - note: Message if folder is empty or doesn't exist
    """
    run_dir = tool_context.state.get(STATE_KEY_RUN_DIR)
    if not run_dir:
        return {
            "error": "run_dir not found in session state"
        }
    
    additional_info_dir = Path(run_dir) / "additional_info"
    
    if not additional_info_dir.exists():
        logger.info("additional_info folder does not exist", extra={
            "agent": "data_analysis", 
            "phase": "check_for_additional_info",
            "path": str(additional_info_dir)
        })
        return {
            "files": [],
            "count": 0,
            "note": "No additional_info folder found"
        }
    
    try:
        files = sorted([f.name for f in additional_info_dir.iterdir() if f.is_file()])
        logger.info("checked additional_info folder", extra={
            "agent": "data_analysis",
            "phase": "check_for_additional_info",
            "count": len(files)
        })
        return {
            "files": files,
            "count": len(files),
            "note": "Additional information files found" if files else "Folder is empty"
        }
    except Exception as e:
        logger.exception("Error reading additional_info folder", extra={
            "agent": "data_analysis",
            "phase": "check_for_additional_info"
        })
        return {
            "files": [],
            "count": 0,
            "error": str(e)
        }


def read_additional_information(file_name: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Read the contents of a file with auxiliary information.
    
    Currently supports markdown files (.md). Other formats may be added later.
    
    Args:
        file_name: Name of the file to read (e.g., "data_dictionary.md")
    
    Returns:
        Dictionary containing:
        - content: File contents as a string
        - format: File format detected (.md)
        - message: Confirmation message
    
    Raises:
        ValueError: If file is not in supported format
        FileNotFoundError: If file does not exist
    """
    run_dir = tool_context.state.get(STATE_KEY_RUN_DIR)
    if not run_dir:
        return {
            "error": "run_dir not found in session state"
        }
    
    additional_info_dir = Path(run_dir) / "additional_info"
    file_path = additional_info_dir / file_name
    
    # Validate file exists
    if not file_path.exists():
        logger.warning("additional_info file not found", extra={
            "agent": "data_analysis",
            "phase": "read_additional_information",
            "file": file_name
        })
        return {
            "error": f"File '{file_name}' not found in additional_info folder"
        }
    
    # Check file format
    if not file_name.endswith('.md'):
        logger.warning("unsupported file format", extra={
            "agent": "data_analysis",
            "phase": "read_additional_information",
            "file": file_name,
            "format": Path(file_name).suffix
        })
        return {
            "error": f"Unsupported file format '{Path(file_name).suffix}'. Currently only .md files are supported."
        }
    
    try:
        content = file_path.read_text(encoding='utf-8')
        logger.info("read additional_info file", extra={
            "agent": "data_analysis",
            "phase": "read_additional_information",
            "file": file_name,
            "size": len(content)
        })
        return {
            "content": content,
            "format": ".md",
            "message": f"Successfully read '{file_name}'"
        }
    except Exception as e:
        logger.exception("Error reading additional_info file", extra={
            "agent": "data_analysis",
            "phase": "read_additional_information",
            "file": file_name
        })
        return {
            "error": f"Failed to read file '{file_name}': {str(e)}"
        }


# Create FunctionTools for use in agents
check_for_additional_info_tool = FunctionTool(func=check_for_additional_info)
read_additional_information_tool = FunctionTool(func=read_additional_information)
