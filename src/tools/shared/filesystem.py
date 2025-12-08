"""
Shared filesystem tools used by multiple agents.

Provides common file operations:
- delete_file: Delete files within allowed paths
- file_exists: Check if a file exists
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger

logger = get_logger(__name__)


def delete_file(
    path: str,
    allowed_paths: list[str] | None = None,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Delete a file from the workspace.
    
    Use this to clean up files during refactoring or when files need to be
    completely rewritten.
    
    Args:
        path: Path to the file to delete (absolute or relative).
        allowed_paths: Optional list of allowed directory paths. If provided,
                      the file must be within one of these directories.
    
    Returns:
        Dictionary with:
        - deleted: Boolean indicating if deletion was successful
        - path: The resolved path that was deleted
        - error: Error message if deletion failed
    
    Note:
        Directories cannot be deleted with this tool.
    """
    path_obj = Path(path)
    
    # Resolve relative paths
    if not path_obj.is_absolute():
        # Try to resolve from tool_context state
        workspace_root = None
        if tool_context:
            workspace_root = tool_context.state.get("workspace_root")
        
        if workspace_root:
            path_obj = Path(workspace_root) / path
        else:
            path_obj = path_obj.resolve()
    
    resolved_path = path_obj.resolve()
    
    # Validate against allowed paths if provided
    if allowed_paths:
        is_allowed = False
        for allowed in allowed_paths:
            allowed_path = Path(allowed).resolve()
            try:
                resolved_path.relative_to(allowed_path)
                is_allowed = True
                break
            except ValueError:
                continue
        
        if not is_allowed:
            logger.warning("delete_file blocked - path not allowed", extra={"path": str(resolved_path)})
            return {
                "deleted": False,
                "error": f"Path not in allowed locations: {resolved_path}",
                "path": str(resolved_path),
            }
    
    if not resolved_path.exists():
        return {
            "deleted": False,
            "error": f"File does not exist: {resolved_path}",
            "path": str(resolved_path),
        }
    
    if not resolved_path.is_file():
        return {
            "deleted": False,
            "error": f"Path is not a file (cannot delete directories): {resolved_path}",
            "path": str(resolved_path),
        }
    
    try:
        resolved_path.unlink()
        
        logger.info("delete_file success", extra={"path": str(resolved_path)})
        
        return {
            "deleted": True,
            "path": str(resolved_path),
        }
        
    except PermissionError:
        logger.error("delete_file permission denied", extra={"path": str(resolved_path)})
        return {
            "deleted": False,
            "error": f"Permission denied: {resolved_path}",
            "path": str(resolved_path),
        }
    except Exception as exc:
        logger.error("delete_file failed", extra={"path": str(resolved_path), "error": str(exc)})
        return {
            "deleted": False,
            "error": f"Failed to delete file: {exc}",
            "path": str(resolved_path),
        }


def file_exists(
    path: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Check if a file exists at the given path.
    
    Args:
        path: Path to check (absolute or relative).
    
    Returns:
        Dictionary with:
        - exists: Boolean indicating if file exists
        - is_file: Boolean indicating if path is a file (vs directory)
        - path: The resolved path
    """
    path_obj = Path(path)
    
    # Resolve relative paths
    if not path_obj.is_absolute():
        workspace_root = None
        if tool_context:
            workspace_root = tool_context.state.get("workspace_root")
        
        if workspace_root:
            path_obj = Path(workspace_root) / path
        else:
            path_obj = path_obj.resolve()
    
    resolved_path = path_obj.resolve()
    
    exists = resolved_path.exists()
    is_file = resolved_path.is_file() if exists else False
    
    return {
        "exists": exists,
        "is_file": is_file,
        "path": str(resolved_path),
    }


# Tool exports
delete_file_tool = FunctionTool(func=delete_file)
file_exists_tool = FunctionTool(func=file_exists)
