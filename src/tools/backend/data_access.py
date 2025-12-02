"""
Data access tools for the Backend Agent.

Provides tools for reading sample data, data profiles, and dashboard concepts.
Also provides the copy_data_to_project function for use in callbacks (not as a tool).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from src.core.logging import get_logger
from src.tools.backend.filesystem import SAMPLE_DASHBOARD_ROOT, _validate_path

logger = get_logger(__name__)


# Maximum rows to return from get_sample_rows (prevents excessive data transfer)
MAX_SAMPLE_ROWS = 5


def get_sample_rows(
    csv_path: str,
    num_rows: int = 5,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the first N rows of a CSV file to understand data structure.
    
    Does not load the entire file into memory - uses polars lazy loading.
    Maximum of 5 rows will be returned regardless of num_rows requested.
    
    Args:
        csv_path: Absolute path to the CSV file.
        num_rows: Number of rows to return (default 5, max 5).
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - columns: List of column names
        - rows: List of dictionaries representing each row
        - total_rows_sampled: Number of rows returned
        - error: Error message if operation failed
    """
    run_dir = tool_context.state.get("run_dir") if tool_context else None
    
    is_valid, resolved_path, error = _validate_path(csv_path, run_dir)
    if not is_valid:
        logger.warning("get_sample_rows blocked", extra={"path": csv_path, "error": error})
        return {"error": error, "path": csv_path}
    
    if not resolved_path.is_file():
        return {"error": f"Not a file: {resolved_path}", "path": str(resolved_path)}
    
    if resolved_path.suffix.lower() != ".csv":
        return {"error": f"Not a CSV file: {resolved_path}", "path": str(resolved_path)}
    
    # Cap num_rows at MAX_SAMPLE_ROWS
    num_rows = min(num_rows, MAX_SAMPLE_ROWS)
    
    try:
        import polars as pl
        
        # Use polars lazy loading for efficient partial CSV reading
        df = pl.scan_csv(str(resolved_path)).head(num_rows).collect()
        
        columns = df.columns
        rows = df.to_dicts()
        
        logger.info(
            "get_sample_rows success",
            extra={"agent": "backend", "path": str(resolved_path), "rows": len(rows)},
        )
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows_sampled": len(rows),
        }
        
    except Exception as exc:
        logger.error("get_sample_rows failed", extra={"path": csv_path, "error": str(exc)})
        return {"error": f"Failed to read CSV: {exc}", "path": str(resolved_path)}


def read_data_profile(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the data profile markdown from the current run's artifacts.
    
    Requires `run_dir` or `data_profile_path` to be set in session state.
    
    Args:
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - content: The markdown content of the data profile
        - path: The resolved path to the data profile
        - error: Error message if operation failed
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    # Try to get path from state
    data_profile_path = tool_context.state.get("data_profile_path")
    run_dir = tool_context.state.get("run_dir")
    
    if data_profile_path:
        profile_path = Path(data_profile_path)
    elif run_dir:
        profile_path = Path(run_dir) / "data_analysis" / "data_profile.md"
    else:
        return {"error": "Neither 'data_profile_path' nor 'run_dir' found in session state"}
    
    if not profile_path.exists():
        return {"error": f"Data profile not found: {profile_path}", "path": str(profile_path)}
    
    try:
        content = profile_path.read_text(encoding="utf-8")
        
        logger.info(
            "read_data_profile success",
            extra={"agent": "backend", "path": str(profile_path)},
        )
        
        return {
            "content": content,
            "path": str(profile_path),
        }
        
    except Exception as exc:
        logger.error("read_data_profile failed", extra={"path": str(profile_path), "error": str(exc)})
        return {"error": f"Failed to read data profile: {exc}", "path": str(profile_path)}


def read_dashboard_concept(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read and parse the dashboard concept JSON from the current run's planner output.
    
    Requires `run_dir` or `dashboard_spec_path` to be set in session state.
    
    Args:
        tool_context: ADK tool context with session state.
        
    Returns:
        Dictionary with:
        - concept: The parsed dashboard concept object
        - path: The resolved path to the dashboard concept file
        - error: Error message if operation failed
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    # Try to get path from state
    dashboard_spec_path = tool_context.state.get("dashboard_spec_path")
    run_dir = tool_context.state.get("run_dir")
    
    if dashboard_spec_path:
        concept_path = Path(dashboard_spec_path)
    elif run_dir:
        concept_path = Path(run_dir) / "planner" / "dashboard_concept.json"
    else:
        return {"error": "Neither 'dashboard_spec_path' nor 'run_dir' found in session state"}
    
    if not concept_path.exists():
        return {"error": f"Dashboard concept not found: {concept_path}", "path": str(concept_path)}
    
    try:
        content = concept_path.read_text(encoding="utf-8")
        concept = json.loads(content)
        
        logger.info(
            "read_dashboard_concept success",
            extra={"agent": "backend", "path": str(concept_path)},
        )
        
        return {
            "concept": concept,
            "path": str(concept_path),
        }
        
    except json.JSONDecodeError as exc:
        logger.error("read_dashboard_concept JSON error", extra={"path": str(concept_path), "error": str(exc)})
        return {"error": f"Invalid JSON in dashboard concept: {exc}", "path": str(concept_path)}
    except Exception as exc:
        logger.error("read_dashboard_concept failed", extra={"path": str(concept_path), "error": str(exc)})
        return {"error": f"Failed to read dashboard concept: {exc}", "path": str(concept_path)}


def copy_data_to_project(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Copy all cleaned data files from run artifacts to the Next.js project's data/ folder.
    
    This is a callback helper function, NOT a tool. It should be called from the
    Dev Orchestrator's before_agent_callback to ensure data is copied before the
    Backend Agent starts creating API routes.
    
    Copies all files from `{run_dir}/data_analysis/cleaned/` to `sample-dashboard/data/`.
    Creates the `data/` directory if it doesn't exist.
    
    Args:
        state: Session state dictionary containing 'run_dir' or 'cleaned_data_path'.
        
    Returns:
        Dictionary with:
        - copied_files: List of dictionaries with source and destination paths
        - destination_dir: Path to the destination data directory
        - total_files: Number of files copied
        - error: Error message if operation failed
    """
    if state is None:
        return {"error": "State not provided"}
    
    # Determine source directory
    cleaned_data_path = state.get("cleaned_data_path")
    run_dir = state.get("run_dir")
    
    if cleaned_data_path:
        # If a specific file path is given, use its parent directory
        source_path = Path(cleaned_data_path)
        if source_path.is_file():
            source_dir = source_path.parent
        else:
            source_dir = source_path
    elif run_dir:
        source_dir = Path(run_dir) / "data_analysis" / "cleaned"
    else:
        return {"error": "Neither 'cleaned_data_path' nor 'run_dir' found in session state"}
    
    if not source_dir.exists():
        return {"error": f"Source directory not found: {source_dir}", "source": str(source_dir)}
    
    if not source_dir.is_dir():
        return {"error": f"Source is not a directory: {source_dir}", "source": str(source_dir)}
    
    # Destination directory in sample-dashboard
    dest_dir = SAMPLE_DASHBOARD_ROOT / "data"
    
    try:
        # Create destination directory if it doesn't exist
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        copied_files: list[dict[str, str]] = []
        
        # Copy all files from source to destination
        for source_file in source_dir.iterdir():
            if source_file.is_file():
                dest_file = dest_dir / source_file.name
                shutil.copy2(source_file, dest_file)
                
                copied_files.append({
                    "source": str(source_file),
                    "destination": str(dest_file),
                    "filename": source_file.name,
                })
        
        if not copied_files:
            return {
                "warning": "No files found in source directory",
                "source": str(source_dir),
                "destination_dir": str(dest_dir),
                "copied_files": [],
                "total_files": 0,
            }
        
        logger.info(
            "copy_data_to_project success",
            extra={
                "agent": "backend",
                "source": str(source_dir),
                "destination": str(dest_dir),
                "files": len(copied_files),
            },
        )
        
        return {
            "copied_files": copied_files,
            "destination_dir": str(dest_dir),
            "total_files": len(copied_files),
        }
        
    except Exception as exc:
        logger.error(
            "copy_data_to_project failed",
            extra={"source": str(source_dir), "error": str(exc)},
        )
        return {"error": f"Failed to copy data files: {exc}", "source": str(source_dir)}


# ============================================================================
# Tool Exports
# ============================================================================

get_sample_rows_tool = FunctionTool(func=get_sample_rows)
read_data_profile_tool = FunctionTool(func=read_data_profile)
read_dashboard_concept_tool = FunctionTool(func=read_dashboard_concept)

# Note: copy_data_to_project is NOT exported as a tool.
# It should be called from a before_agent_callback in the Dev Orchestrator,
# not by the agent itself.
