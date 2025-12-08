"""
Shared data access tools used by multiple agents.

Provides common data operations:
- get_sample_rows: Read sample rows from CSV files

Note: For reading JSON files, use the MCP filesystem read_file tool instead.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger
from src.tools.utils import (
    SAMPLE_DASHBOARD_ROOT,
    BACKEND_DEV_ALLOWED_PATHS,
    TESTER_ALLOWED_PATHS,
    validate_path,
)

logger = get_logger(__name__)


# Default maximum rows to return (can be overridden per-tool)
DEFAULT_MAX_SAMPLE_ROWS = 5

# Combined allowed paths for data access (union of all agent paths)
DATA_ALLOWED_PATHS = list(set(BACKEND_DEV_ALLOWED_PATHS + TESTER_ALLOWED_PATHS))


def _validate_path(
    requested_path: str | Path,
    allow_new: bool = False,
) -> tuple[bool, Path, str]:
    """
    Validate that a requested path is within allowed data paths.
    
    Args:
        requested_path: The path the agent wants to access.
        allow_new: If True, allows paths that don't exist yet.
        
    Returns:
        Tuple of (is_valid, resolved_path, error_message).
    """
    return validate_path(
        requested_path=requested_path,
        allowed_paths=DATA_ALLOWED_PATHS,
        allow_new=allow_new,
    )


def get_sample_rows(
    csv_path: str,
    num_rows: int = 5,
    max_rows: int = DEFAULT_MAX_SAMPLE_ROWS,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read sample rows from a CSV file to understand data structure.
    
    Uses polars lazy loading for efficiency.
    
    Args:
        csv_path: Path to the CSV file (absolute or relative).
        num_rows: Number of rows to return (default 5).
        max_rows: Maximum allowed rows (enforced limit, default 5).
    
    Returns:
        Dictionary with:
        - columns: List of column names
        - rows: List of row dictionaries
        - total_rows_sampled: Number of rows returned
        - error: Error message if reading failed
    """
    # Resolve and validate path
    is_valid, resolved_path, error_msg = _validate_path(csv_path, allow_new=False)
    
    if not is_valid:
        return {"error": f"Path not in allowed locations: {csv_path}. {error_msg}"}
    
    if not resolved_path.exists():
        return {"error": f"File not found: {csv_path}", "path": str(resolved_path)}
    
    if not resolved_path.is_file():
        return {"error": f"Not a file: {resolved_path}", "path": str(resolved_path)}
    
    if resolved_path.suffix.lower() != ".csv":
        return {"error": f"Not a CSV file: {resolved_path}", "path": str(resolved_path)}
    
    # Cap num_rows at max_rows
    num_rows = min(num_rows, max_rows)
    
    try:
        import polars as pl
        
        # Use polars lazy loading for efficient partial CSV reading
        df = pl.scan_csv(str(resolved_path)).head(num_rows).collect()
        
        columns = df.columns
        rows = df.to_dicts()
        
        logger.info(
            "get_sample_rows success",
            extra={"path": str(resolved_path), "rows": len(rows)},
        )
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows_sampled": len(rows),
            "path": str(resolved_path),
        }
        
    except Exception as exc:
        logger.error("get_sample_rows failed", extra={"path": csv_path, "error": str(exc)})
        return {"error": f"Failed to read CSV: {exc}", "path": str(resolved_path)}


# Tool exports
get_sample_rows_tool = FunctionTool(func=get_sample_rows)
