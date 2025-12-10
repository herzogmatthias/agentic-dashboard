"""
Planner Agent tools.

Provides tools for reading data analysis artifacts and previewing JSON files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.agents.manager.state import STATE_KEY_RUN_DIR
from src.core.logging import get_logger
from src.tools.shared import inspect_json_preview_tool  # Re-export from shared

logger = get_logger(__name__)


def read_data_profile(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the DataProfile JSON from the current run's artifacts.
    
    Returns minified JSON content from {run_dir}/data_profile.json.
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    data_profile_path = tool_context.state.get("data_profile_path")
    run_dir = tool_context.state.get(STATE_KEY_RUN_DIR)
    
    if data_profile_path:
        profile_path = Path(data_profile_path)
    elif run_dir:
        profile_path = Path(run_dir) / "data_profile.json"
    else:
        return {"error": "Neither 'data_profile_path' nor 'run_dir' found in session state"}
    
    if not profile_path.exists():
        return {"error": f"Data profile not found: {profile_path}", "path": str(profile_path)}
    
    try:
        content = json.loads(profile_path.read_text(encoding="utf-8"))
        minified = json.dumps(content, separators=(",", ":"))
        
        logger.info(
            "read_data_profile success",
            extra={"agent": "planner", "path": str(profile_path)},
        )
        
        return {
            "profile": minified,
            "path": str(profile_path),
        }
        
    except json.JSONDecodeError as exc:
        logger.error("read_data_profile JSON error", extra={"path": str(profile_path), "error": str(exc)})
        return {"error": f"Invalid JSON: {exc}", "path": str(profile_path)}
    except Exception as exc:
        logger.error("read_data_profile failed", extra={"path": str(profile_path), "error": str(exc)})
        return {"error": f"Failed to read data profile: {exc}", "path": str(profile_path)}


def read_cleaning_summary(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the CleaningSummary JSON from the current run's artifacts.
    
    Returns minified JSON content from {run_dir}/cleaning_summary.json.
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    cleaning_summary_path = tool_context.state.get("cleaning_summary_path")
    run_dir = tool_context.state.get(STATE_KEY_RUN_DIR)
    
    if cleaning_summary_path:
        summary_path = Path(cleaning_summary_path)
    elif run_dir:
        summary_path = Path(run_dir) / "cleaning_summary.json"
    else:
        return {"error": "Neither 'cleaning_summary_path' nor 'run_dir' found in session state"}
    
    if not summary_path.exists():
        return {"error": f"Cleaning summary not found: {summary_path}", "path": str(summary_path)}
    
    try:
        content = json.loads(summary_path.read_text(encoding="utf-8"))
        minified = json.dumps(content, separators=(",", ":"))
        
        logger.info(
            "read_cleaning_summary success",
            extra={"agent": "planner", "path": str(summary_path)},
        )
        
        return {
            "summary": minified,
            "path": str(summary_path),
        }
        
    except json.JSONDecodeError as exc:
        logger.error("read_cleaning_summary JSON error", extra={"path": str(summary_path), "error": str(exc)})
        return {"error": f"Invalid JSON: {exc}", "path": str(summary_path)}
    except Exception as exc:
        logger.error("read_cleaning_summary failed", extra={"path": str(summary_path), "error": str(exc)})
        return {"error": f"Failed to read cleaning summary: {exc}", "path": str(summary_path)}


def read_metrics_summary(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the MetricsSummary JSON from the current run's artifacts (if available).
    
    Returns minified JSON content from {run_dir}/metrics_summary.json.
    Not all runs produce a metrics summary - returns error if not found.
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    metrics_summary_path = tool_context.state.get("metrics_summary_path")
    run_dir = tool_context.state.get(STATE_KEY_RUN_DIR)
    
    if metrics_summary_path:
        summary_path = Path(metrics_summary_path)
    elif run_dir:
        summary_path = Path(run_dir) / "metrics_summary.json"
    else:
        return {"error": "Neither 'metrics_summary_path' nor 'run_dir' found in session state"}
    
    if not summary_path.exists():
        return {"error": f"Metrics summary not found: {summary_path}", "path": str(summary_path)}
    
    try:
        content = json.loads(summary_path.read_text(encoding="utf-8"))
        minified = json.dumps(content, separators=(",", ":"))
        
        logger.info(
            "read_metrics_summary success",
            extra={"agent": "planner", "path": str(summary_path)},
        )
        
        return {
            "summary": minified,
            "path": str(summary_path),
        }
        
    except json.JSONDecodeError as exc:
        logger.error("read_metrics_summary JSON error", extra={"path": str(summary_path), "error": str(exc)})
        return {"error": f"Invalid JSON: {exc}", "path": str(summary_path)}
    except Exception as exc:
        logger.error("read_metrics_summary failed", extra={"path": str(summary_path), "error": str(exc)})
        return {"error": f"Failed to read metrics summary: {exc}", "path": str(summary_path)}


def get_sample_rows(
    num_rows: int = 5,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the first N rows of the cleaned CSV file to understand data structure.
    
    Uses polars lazy loading for efficiency. Maximum of 5 rows returned.
    Reads from the cleaned.csv in {run_dir}/cleaned/.
    
    Args:
        num_rows: Number of rows to return (default 5, max 5).
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    run_dir = tool_context.state.get(STATE_KEY_RUN_DIR)
    if not run_dir:
        return {"error": "'run_dir' not found in session state"}
    
    # Look for cleaned.csv in the cleaned directory
    cleaned_dir = Path(run_dir) / "cleaned"
    csv_path = cleaned_dir / "cleaned.csv"
    
    if not csv_path.exists():
        # Try alternative paths
        alt_paths = [
            Path(run_dir) / "cleaned.csv",
            cleaned_dir / "data.csv",
        ]
        for alt in alt_paths:
            if alt.exists():
                csv_path = alt
                break
        else:
            return {"error": f"Cleaned CSV not found in {cleaned_dir}", "searched": str(cleaned_dir)}
    
    # Cap num_rows at 5
    num_rows = min(num_rows, 5)
    
    try:
        import polars as pl
        
        df = pl.scan_csv(str(csv_path)).head(num_rows).collect()
        
        columns = df.columns
        rows = df.to_dicts()
        
        logger.info(
            "get_sample_rows success",
            extra={"agent": "planner", "path": str(csv_path), "rows": len(rows)},
        )
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows_sampled": len(rows),
            "source": str(csv_path),
        }
        
    except Exception as exc:
        logger.error("get_sample_rows failed", extra={"path": str(csv_path), "error": str(exc)})
        return {"error": f"Failed to read CSV: {exc}", "path": str(csv_path)}


# ============================================================================
# Tool Exports
# ============================================================================

read_data_profile_tool = FunctionTool(func=read_data_profile)
read_cleaning_summary_tool = FunctionTool(func=read_cleaning_summary)
read_metrics_summary_tool = FunctionTool(func=read_metrics_summary)
get_sample_rows_tool = FunctionTool(func=get_sample_rows)
# inspect_json_preview_tool is imported from src.tools.shared
