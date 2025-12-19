"""
Data access tools for the Backend Dev Agent.

Provides tools for loading data profiles and backend manifests.
For sample CSV data, use the shared get_sample_rows tool.
For file copying, use src.core.utils.copy_data_to_project callback.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger

logger = get_logger(__name__)


def load_data_profile(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Load the minified data profile JSON for the current run.
    
    The data profile contains information about the dataset structure:
    - Column names and types
    - Cardinality and uniqueness
    - Missing value statistics
    - Domain signals (date columns, identifiers, etc.)
    
    Use this tool when you need detailed information about the dataset
    to implement your artifact correctly.
    
    Returns:
        Dictionary with:
        - profile: The minified data profile JSON
        - error: Error message if loading failed
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    run_dir = tool_context.state.get("run_dir")
    if not run_dir:
        return {"error": "run_dir not found in session state"}
    
    run_path = Path(run_dir)
    
    profile_json_path = run_path / "data_profile.json"
    
    if not profile_json_path.exists():
        return {
            "error": f"Data profile not found at {profile_json_path}",
            "run_dir": str(run_dir),
        }
    
    try:
        with open(profile_json_path, "r", encoding="utf-8") as f:
            profile_data = json.load(f)
        
        # Return minified JSON string
        minified = json.dumps(profile_data, separators=(",", ":"))
        
        logger.info(
            "load_data_profile success",
            extra={"agent": "backend_dev", "path": str(profile_json_path)},
        )
        
        return {
            "profile": minified,
            "path": str(profile_json_path),
        }
        
    except json.JSONDecodeError as exc:
        logger.error(
            "load_data_profile failed - invalid JSON",
            extra={"path": str(profile_json_path), "error": str(exc)},
        )
        return {"error": f"Invalid JSON in data profile: {exc}"}
    except Exception as exc:
        logger.error(
            "load_data_profile failed",
            extra={"path": str(profile_json_path), "error": str(exc)},
        )
        return {"error": f"Failed to load data profile: {exc}"}


def read_backend_manifest(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the backend manifest from the current run.
    
    The backend manifest contains information about all artifacts:
    - List of artifacts with their status
    - File paths for each artifact
    - Dependencies between artifacts
    
    Use this tool to understand the overall structure of what was built
    or what needs to be built.
    
    Returns:
        Dictionary with:
        - manifest: The manifest data
        - path: Path to the manifest file
        - error: Error message if loading failed
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    run_dir = tool_context.state.get("run_dir")
    if not run_dir:
        return {"error": "run_dir not found in session state"}
    
    run_path = Path(run_dir)
    
    manifest_path = run_path / "backend_manifest.json"
    
    if not manifest_path.exists():
        return {
            "error": "Backend manifest not found",
            "searched_path": str(manifest_path),
            "run_dir": str(run_dir),
        }
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        
        logger.info(
            "read_backend_manifest success",
            extra={"agent": "backend_dev", "path": str(manifest_path)},
        )
        
        return {
            "manifest": manifest_data,
            "path": str(manifest_path),
        }
        
    except json.JSONDecodeError as exc:
        logger.error(
            "read_backend_manifest failed - invalid JSON",
            extra={"path": str(manifest_path), "error": str(exc)},
        )
        return {"error": f"Invalid JSON in backend manifest: {exc}", "path": str(manifest_path)}
    except Exception as exc:
        logger.error(
            "read_backend_manifest failed",
            extra={"path": str(manifest_path), "error": str(exc)},
        )
        return {"error": f"Failed to read backend manifest: {exc}", "path": str(manifest_path)}


# ============================================================================
# Tool Exports
# ============================================================================

load_data_profile_tool = FunctionTool(func=load_data_profile)
read_backend_manifest_tool = FunctionTool(func=read_backend_manifest)
# inspect_json_preview_tool is imported from src.tools.shared
