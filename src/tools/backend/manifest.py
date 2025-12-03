"""
Backend manifest writing tool.

Provides the write_backend_manifest tool for persisting the BackendManifest
to the run directory after the Backend Agent completes its work.
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


# ============================================================================
# Tool Implementation
# ============================================================================


def write_backend_manifest(
    manifest: BackendManifest,
    tool_context: ToolContext | None = None,
) -> dict[str, Any]:
    """
    Write the backend manifest to {run_dir}/dev/backend_manifest.json.
    
    The manifest uses the BackendManifest Pydantic model. The created_at field
    is optional and will be auto-populated if not provided.
    
    Updates session state with backend_manifest_path and backend_status.
    
    Args:
        manifest: BackendManifest object with run_id, data_source, models, routes, validation
    
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
        
        # Determine backend_status based on validation results
        validation = validated_manifest.validation
        if validation.lint_passed and validation.build_passed:
            tool_context.state["backend_status"] = BackendStatus.SUCCESS.value
        elif validation.lint_passed or validation.build_passed:
            tool_context.state["backend_status"] = BackendStatus.PARTIAL.value
        else:
            tool_context.state["backend_status"] = BackendStatus.FAILED.value
        
        logger.info(
            "Backend manifest written",
            extra={
                "agent": "backend",
                "phase": "write_manifest",
                "path": str(manifest_path),
                "routes_count": len(validated_manifest.routes),
                "models_count": len(validated_manifest.models),
                "status": tool_context.state["backend_status"]
            }
        )
        
        return {
            "success": True,
            "path": str(manifest_path.resolve()),
            "routes_count": len(validated_manifest.routes),
            "models_count": len(validated_manifest.models),
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
