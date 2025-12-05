"""
Backend manifest writing tool.

Provides the write_backend_manifest tool for persisting the BackendManifest
to the run directory after the Backend Agent completes its work.

The manifest tool now includes validation gating:
- Runs lint and type-check before writing
- Only allows manifest write if there are no errors
- Returns detailed error information if validation fails
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from src.core.logging import get_logger
from src.models.backend_manifest import (
    BackendManifest,
    BackendStatus,
    DataSourceInfo,
    ModelInfo,
    RouteInfo,
    ValidationResult,
)
from src.tools.backend.validation import run_lint, run_type_check

logger = get_logger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Output directory name within run_dir
DEV_OUTPUT_DIR = "dev"

# Manifest filename
MANIFEST_FILENAME = "backend_manifest.json"


# ============================================================================
# Helper Functions (for tests)
# ============================================================================


def _ensure_created_at(manifest_dict: dict[str, Any]) -> dict[str, Any]:
    """Ensure manifest dict has created_at timestamp, auto-populating if missing."""
    if not manifest_dict.get("created_at"):
        manifest_dict["created_at"] = datetime.now().isoformat()
    return manifest_dict


def _validate_manifest(manifest_dict: dict[str, Any]) -> BackendManifest:
    """Validate manifest dict against BackendManifest schema."""
    try:
        return BackendManifest.model_validate(manifest_dict)
    except Exception as e:
        raise ValueError(f"Manifest validation failed: {e}") from e


def _ensure_manifest_created_at(manifest: BackendManifest) -> BackendManifest:
    """Ensure BackendManifest has created_at, returning updated copy if needed."""
    if not manifest.created_at:
        return manifest.model_copy(update={"created_at": datetime.now().isoformat()})
    return manifest


def _run_validation_checks() -> dict[str, Any]:
    """
    Run lint and type-check validations.
    
    Returns:
        Dict with lint_result, type_check_result, and overall passed status
    """
    lint_result = run_lint()
    type_check_result = run_type_check()
    
    return {
        "lint_result": lint_result,
        "type_check_result": type_check_result,
        "lint_passed": lint_result.get("passed", False),
        "type_check_passed": type_check_result.get("passed", False),
        "all_passed": lint_result.get("passed", False) and type_check_result.get("passed", False),
    }


# ============================================================================
# Tool Implementation
# ============================================================================


def write_backend_manifest(
    manifest: BackendManifest,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Write the backend manifest to {run_dir}/dev/backend_manifest.json.
    
    **IMPORTANT: This tool includes validation gating.**
    
    Before writing the manifest, this tool runs:
    1. `npm run lint` - ESLint validation
    2. `npm run type-check` - TypeScript type checking
    
    The manifest will ONLY be written if BOTH validations pass.
    If validation fails, the tool returns error details so you can fix issues first.
    
    The manifest uses the BackendManifest Pydantic model. The created_at field
    is optional and will be auto-populated if not provided.
    
    Updates session state with backend_manifest_path and backend_status.
    
    Args:
        manifest: BackendManifest object with run_id, data_source, models, routes, validation
    
    Returns:
        On success: {success: True, path: str, routes_count: int, models_count: int}
        On validation failure: {success: False, validation_failed: True, lint_errors: str, type_check_errors: str}
        On other error: {success: False, error: str}
    
    See BackendManifest schema in src/models/backend_manifest.py for required fields.
    """
    try:
        # Get run_dir from state
        if tool_context is None or "run_dir" not in tool_context.state:
            return {
                "success": False,
                "path": None,
                "error": "ToolContext or run_dir missing; cannot write backend manifest.",
            }
        
        run_dir = Path(tool_context.state["run_dir"])
        
        # Run validation checks BEFORE writing
        logger.info(
            "Running validation checks before manifest write",
            extra={"agent": "backend", "phase": "write_manifest"}
        )
        
        validation = _run_validation_checks()
        
        if not validation["all_passed"]:
            # Build detailed error response
            error_response: dict[str, Any] = {
                "success": False,
                "validation_failed": True,
                "message": "Manifest cannot be written until lint and type-check pass. Fix the errors below and try again.",
            }
            
            if not validation["lint_passed"]:
                lint_result = validation["lint_result"]
                error_response["lint_errors"] = lint_result.get("stdout", "") + "\n" + lint_result.get("stderr", "")
                error_response["lint_exit_code"] = lint_result.get("exit_code")
            
            if not validation["type_check_passed"]:
                tc_result = validation["type_check_result"]
                error_response["type_check_errors"] = tc_result.get("stdout", "") + "\n" + tc_result.get("stderr", "")
                error_response["type_check_exit_code"] = tc_result.get("exit_code")
            
            logger.warning(
                "Manifest write blocked: validation failed",
                extra={
                    "agent": "backend",
                    "phase": "write_manifest",
                    "lint_passed": validation["lint_passed"],
                    "type_check_passed": validation["type_check_passed"],
                }
            )
            
            return error_response
        
        logger.info(
            "Validation passed, proceeding to write manifest",
            extra={"agent": "backend", "phase": "write_manifest"}
        )
        
        # Convert dict to BackendManifest if needed (ADK passes dicts from LLM)
        if isinstance(manifest, dict):
            # Ensure created_at is present before validation
            manifest_dict = _ensure_created_at(manifest)
            validated_manifest = _validate_manifest(manifest_dict)
        else:
            # Already a BackendManifest, just ensure created_at
            validated_manifest = _ensure_manifest_created_at(manifest)
        
        # Create output directory
        output_dir = run_dir / DEV_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write manifest as JSON
        manifest_path = output_dir / MANIFEST_FILENAME
        manifest_json = validated_manifest.model_dump_json(indent=2)
        manifest_path.write_text(manifest_json, encoding="utf-8")
        
        # Update session state
        tool_context.state["backend_manifest_path"] = str(manifest_path.resolve())
        
        # Since validation passed, status is SUCCESS
        tool_context.state["backend_status"] = BackendStatus.SUCCESS.value
        
        logger.info(
            "Backend manifest written",
            extra={
                "agent": "backend",
                "phase": "write_manifest",
                "path": str(manifest_path),
                "routes_count": len(validated_manifest.routes),
                "models_count": len(validated_manifest.models),
                "status": BackendStatus.SUCCESS.value
            }
        )
        
        return {
            "success": True,
            "path": str(manifest_path.resolve()),
            "routes_count": len(validated_manifest.routes),
            "models_count": len(validated_manifest.models),
            "validation": {
                "lint_passed": True,
                "type_check_passed": True,
            }
        }
        
    except Exception as e:
        logger.exception(
            "Error writing backend manifest",
            extra={"agent": "backend", "phase": "write_manifest"}
        )
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# ADK Tool Registration
# ============================================================================

write_backend_manifest_tool = FunctionTool(func=write_backend_manifest)
