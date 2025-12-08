"""
Context tools for the Testing Agent.

Provides tools for reading dev reports and other context needed for test generation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.tool_context import ToolContext

from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Tool Implementations
# ============================================================================


def read_dev_report(
    artifact_id: str,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the dev report for a specific artifact from the current run.
    
    Dev reports contain information about what was implemented:
    - Files created/modified (API routes, helpers, models)
    - Endpoints and their structure
    - Implementation notes
    
    Use this tool to understand what needs to be tested for a given artifact.
    
    Args:
        artifact_id: The artifact identifier to get the dev report for.
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    run_dir = tool_context.state.get("run_dir")
    if not run_dir:
        return {"error": "run_dir not found in session state"}
    
    run_path = Path(run_dir)
    
    # Dev reports are stored at {run_dir}/dev_reports/{artifact_id}.json
    dev_report_dir = run_path / "dev_reports"
    dev_report_path = dev_report_dir / f"{artifact_id}.json"
    
    if not dev_report_path.exists():
        # Try alternative location
        alt_path = run_path / f"dev_report_{artifact_id}.json"
        if alt_path.exists():
            dev_report_path = alt_path
        else:
            return {
                "error": f"Dev report not found for artifact '{artifact_id}'",
                "searched_paths": [str(dev_report_path), str(alt_path)],
                "run_dir": str(run_dir),
            }
    
    try:
        with open(dev_report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
        
        logger.info(
            "read_dev_report success",
            extra={"agent": "tester", "artifact_id": artifact_id, "path": str(dev_report_path)},
        )
        
        return {
            "artifact_id": artifact_id,
            "report": report_data,
            "path": str(dev_report_path),
        }
        
    except json.JSONDecodeError as exc:
        logger.error(
            "read_dev_report failed - invalid JSON",
            extra={"path": str(dev_report_path), "error": str(exc)},
        )
        return {"error": f"Invalid JSON in dev report: {exc}", "path": str(dev_report_path)}
    except Exception as exc:
        logger.error(
            "read_dev_report failed",
            extra={"path": str(dev_report_path), "error": str(exc)},
        )
        return {"error": f"Failed to read dev report: {exc}", "path": str(dev_report_path)}


def read_backend_manifest(
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Read the backend manifest from the current run.
    
    The backend manifest contains information about all artifacts:
    - List of artifacts with their status
    - File paths for each artifact
    - Dependencies between artifacts
    
    Use this tool to understand the overall structure of what was built.
    """
    if tool_context is None:
        return {"error": "Tool context not provided"}
    
    run_dir = tool_context.state.get("run_dir")
    if not run_dir:
        return {"error": "run_dir not found in session state"}
    
    run_path = Path(run_dir)
    
    # Backend manifest is stored at {run_dir}/backend_manifest.json
    manifest_path = run_path / "backend_manifest.json"
    
    if not manifest_path.exists():
        return {
            "error": f"Backend manifest not found",
            "searched_path": str(manifest_path),
            "run_dir": str(run_dir),
        }
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        
        logger.info(
            "read_backend_manifest success",
            extra={"agent": "tester", "path": str(manifest_path)},
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

read_dev_report_tool = FunctionTool(func=read_dev_report)
read_backend_manifest_tool = FunctionTool(func=read_backend_manifest)
