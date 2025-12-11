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

# Data folder is ONLY for sample_dashboard data reads, completely independent of filesystem_mcp
DATA_ALLOWED_PATHS = [SAMPLE_DASHBOARD_ROOT / "data"]


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
    filename: str,
    num_rows: int = 5,
    max_rows: int = DEFAULT_MAX_SAMPLE_ROWS,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read sample rows from a CSV file in the cleaned/ folder.
    
    Always resolves to: {run_dir}/cleaned/{filename}
    
    Uses polars lazy loading for efficiency.
    
    Args:
        filename: Simple filename (e.g., "cleaned.csv", "features.csv")
                  Will be resolved to {run_dir}/cleaned/{filename}
        num_rows: Number of rows to return (default 5).
        max_rows: Maximum allowed rows (enforced limit, default 5).
        tool_context: Tool context with state access (required for run_dir).
    
    Returns:
        Dictionary with:
        - columns: List of column names
        - rows: List of row dictionaries
        - total_rows_sampled: Number of rows returned
        - path: Full resolved path that was read
        - error: Error message if reading failed
    """
    if not tool_context:
        return {"error": "Tool context required for run_dir resolution"}
    
    run_dir = tool_context.state.get("run_dir")
    if not run_dir:
        return {"error": "run_dir not found in session state"}
    
    # Resolve to cleaned/ folder
    resolved_path = Path(run_dir) / "cleaned" / filename
    
    if not resolved_path.exists():
        return {
            "error": f"File not found: {filename}",
            "expected_location": str(resolved_path),
        }
    
    if not resolved_path.is_file():
        return {
            "error": f"Not a file: {filename}",
            "path": str(resolved_path),
        }
    
    if resolved_path.suffix.lower() != ".csv":
        return {
            "error": f"Not a CSV file: {filename} (expected .csv extension)",
            "path": str(resolved_path),
        }
    
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
            extra={"data_filename": filename, "rows": len(rows)},
        )
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows_sampled": len(rows),
            "path": str(resolved_path),
        }
        
    except Exception as exc:
        logger.error("get_sample_rows failed", extra={"data_filename": filename, "error": str(exc)})
        return {
            "error": f"Failed to read CSV: {exc}",
            "path": str(resolved_path),
        }


# Tool exports
get_sample_rows_tool = FunctionTool(func=get_sample_rows)
