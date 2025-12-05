"""
Data access tools for the Backend Agent.

Provides tools for reading sample data.
Also provides the copy_data_to_project function for use in callbacks (not as a tool).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.tools.backend.filesystem import SAMPLE_DASHBOARD_ROOT, _validate_path
from src.tools.shared import inspect_json_preview_tool  # Re-export from shared

logger = get_logger(__name__)


# Maximum rows to return from get_sample_rows (prevents excessive data transfer)
# Keep low (1) for large cleaned datasets to avoid token bloat
MAX_SAMPLE_ROWS = 1


def get_sample_rows(
    csv_path: str,
    num_rows: int = 5,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the first N rows of a CSV file to understand data structure.
    
    Uses polars lazy loading for efficiency. Maximum of 5 rows returned.
    
    Args:
        csv_path: Absolute path to the CSV file.
        num_rows: Number of rows to return (default 5, max 5).
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


def copy_data_to_project(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Copy all cleaned data files from run artifacts to the Next.js project's data/ folder.
    
    This is a callback helper function, NOT a tool. It should be called from the
    Dev Orchestrator's before_agent_callback to ensure data is copied before the
    Backend Agent starts creating API routes.
    
    Copies all files from `{run_dir}/cleaned/` to `sample-dashboard/data/`.
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
        # Cleaned data is at {run_dir}/cleaned/
        source_dir = Path(run_dir) / "cleaned"
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
# inspect_json_preview_tool is imported from src.tools.shared

# Note: copy_data_to_project is NOT exported as a tool.
# It is a callback helper function.
