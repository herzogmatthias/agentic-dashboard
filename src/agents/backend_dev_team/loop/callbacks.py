"""
Loop Agent callbacks and state initialization helpers.

State initialization for the Dev Agent happens ONCE at the start of the
Loop Agent's _run_async_impl, not on every Dev Agent invocation.

Callbacks (using ADK built-in before_agent_callback / after_agent_callback):
- before_loop_callback: Initialize state for standalone testing
  (loads artifact from backend_todos.json if not provided)
- after_loop_callback: Persist BackendManifestEntry after successful loop

These callbacks use the standard ADK CallbackContext pattern.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from src.core.logging import get_logger
from src.agents.backend_dev_team.loop.tools import (
    STATE_KEY_RUN_DIR,
    STATE_KEY_BACKEND_TODO_LIST,
    STATE_KEY_LOOP_RESULT,
)

from src.tools.utils.paths import SAMPLE_DASHBOARD_ROOT

logger = get_logger(__name__)


# =============================================================================
# State Keys for Dev Agent
# =============================================================================

STATE_KEY_WORKSPACE_ROOT = "workspace_root"
STATE_KEY_PREVIOUS_SUMMARIES = "previous_summaries"
STATE_KEY_CLEANED_DATA_FILES = "cleaned_data_files"
STATE_KEY_METRICS_REF_CONTEXT = "metrics_ref_context"


# Default run directory for standalone testing (same pattern as planner)
DEFAULT_TEST_RUN_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "agentic-dashboard" / "runs" / "run_20251210_162522"


# =============================================================================
# Before Loop Callback (for standalone testing)
# =============================================================================

def before_loop_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Initialize state for the Loop Agent before execution.
    
    Uses ADK built-in before_agent_callback pattern.
    
    This callback enables standalone testing by:
    1. Setting run_dir to DEFAULT_TEST_RUN_DIR if not present
    2. Loading backend_todo_list from backend_todos.json if not present
    
    Note: The loop now processes ALL pending artifacts, not just one.
    
    Args:
        callback_context: ADK CallbackContext with access to state
        
    Returns:
        None to continue with agent execution, or Content to skip agent and return that content
    """
    state = callback_context.state
    try:
        # 1. Set run_dir if not present (standalone testing mode)
        if STATE_KEY_RUN_DIR not in state or state[STATE_KEY_RUN_DIR] is None:
            run_dir = DEFAULT_TEST_RUN_DIR.resolve()
            state[STATE_KEY_RUN_DIR] = str(run_dir)
            logger.info(
                f"Loop agent using default test run: {run_dir}",
                extra={
                    "agent": "loop",
                    "phase": "before_callback",
                    "standalone": True,
                }
            )
        else:
            run_dir = Path(state[STATE_KEY_RUN_DIR])
        
        # 2. Load backend_todo_list if not present (standalone testing mode)
        if STATE_KEY_BACKEND_TODO_LIST not in state or state[STATE_KEY_BACKEND_TODO_LIST] is None:
            todo_list = _load_backend_todos(run_dir)
            if todo_list:
                state[STATE_KEY_BACKEND_TODO_LIST] = todo_list
                pending_count = len([a for a in todo_list.get("artifacts", []) if a.get("status") == "pending"])
                logger.info(
                    f"Loaded backend_todo_list with {pending_count} pending artifacts",
                    extra={
                        "agent": "loop",
                        "phase": "before_callback",
                        "pending_artifacts": pending_count,
                    }
                )
            else:
                logger.warning(
                    "No backend_todos.json found for standalone testing",
                    extra={"agent": "loop", "phase": "before_callback"}
                )
        
        logger.info(
            "Loop agent before_callback completed",
            extra={
                "agent": "loop",
                "phase": "before_callback",
                "run_dir": str(run_dir),
                "has_todo_list": STATE_KEY_BACKEND_TODO_LIST in state and state[STATE_KEY_BACKEND_TODO_LIST] is not None,
            }
        )
        
        if STATE_KEY_WORKSPACE_ROOT not in state:
            state[STATE_KEY_WORKSPACE_ROOT] = str(SAMPLE_DASHBOARD_ROOT.resolve())
        
        # Initialize previous_summaries if not present
        if STATE_KEY_PREVIOUS_SUMMARIES not in state:
            state[STATE_KEY_PREVIOUS_SUMMARIES] = []
        
        return None  # Continue with agent execution

    except Exception as e:
        logger.exception(
            f"Error in before_loop_callback: {e}",
            extra={"agent": "loop", "phase": "before_callback"}
        )
        return None  # Continue even if callback fails


def _load_backend_todos(run_dir: Path) -> Optional[dict[str, Any]]:
    """
    Load the full backend_todos.json file.
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        Full todo list dict with artifacts array, or None if not found
    """
    todos_path = run_dir / "backend_dev_team" / "backend_todos.json"
    
    if not todos_path.exists():
        logger.debug(f"backend_todos.json not found at {todos_path}")
        return None
    
    try:
        with open(todos_path, "r", encoding="utf-8") as f:
            todos = json.load(f)
        return todos
        
    except Exception as e:
        logger.warning(f"Failed to load backend_todos.json: {e}")
        return None


def _load_first_pending_artifact(run_dir: Path) -> Optional[dict[str, Any]]:
    """
    Load the first pending artifact from backend_todos.json.
    
    DEPRECATED: Use _load_backend_todos instead, as the loop now processes all artifacts.
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        First artifact with status='pending', or None if not found
    """
    todos = _load_backend_todos(run_dir)
    if not todos:
        return None
    
    artifacts = todos.get("artifacts", [])
    for artifact in artifacts:
        if artifact.get("status") == "pending":
            return artifact
    
    logger.debug("No pending artifacts in backend_todos.json")
    return None


# =============================================================================
# After Loop Callback (for manifest persistence)
# =============================================================================

def after_loop_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Called after the loop completes (not after each artifact).
    
    In the dev-only flow, manifest entries are persisted within the loop via
    persist_artifact_manifest_entry(). This callback is now primarily for
    logging and cleanup.
    
    Args:
        callback_context: ADK CallbackContext with access to state
        
    Returns:
        None to continue normally, or Content to append to event history
    """
    state = callback_context.state
    try:
        loop_result = state.get(STATE_KEY_LOOP_RESULT)
        logger.info(
            f"Loop completed with result: {loop_result}",
            extra={
                "agent": "loop",
                "phase": "after_callback",
                "loop_result": loop_result,
            }
        )
        return None
        
    except Exception as e:
        logger.exception(
            f"Error in after_loop_callback: {e}",
            extra={"agent": "loop", "phase": "after_callback"}
        )
        return None


def persist_artifact_manifest_entry(
    run_dir: str,
    artifact: dict[str, Any],
    dev_result: dict[str, Any] | None,
) -> bool:
    """
    Persist a manifest entry for a completed artifact.
    
    Called from within the loop after each successful artifact.
    Builds entry from dev_result only (dev-only flow, no tester).
    
    Args:
        run_dir: Path to run directory
        artifact: The artifact that was processed
        dev_result: BackendDevResult from Dev Agent
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Build manifest entry from dev_result
        entry = _build_manifest_entry_from_dev_report(
            artifact=artifact,
            dev_result=dev_result,
            iteration_count=1,
        )
        
        if entry is None:
            logger.warning(
                f"Failed to build manifest entry for {artifact.get('id')}",
                extra={"artifact_id": artifact.get("id")}
            )
            return False
        
        # Persist to manifest
        success = _persist_manifest_entry(run_dir, entry)
        
        if success:
            logger.info(
                f"Persisted manifest entry for artifact: {entry['artifact_id']}",
                extra={
                    "artifact_id": entry["artifact_id"],
                    "code_path": entry.get("code_path"),
                }
            )
        
        return success
        
    except Exception as e:
        logger.exception(f"Error persisting manifest entry: {e}")
        return False


def _build_manifest_entry_from_dev_report(
    artifact: dict[str, Any],
    dev_result: dict[str, Any] | None,
    iteration_count: int = 1,
) -> Optional[dict[str, Any]]:
    """
    Build a BackendManifestEntry dict from Dev Agent result ONLY (no tester).
    
    Args:
        artifact: The processed artifact (PlannerArtifactTodo as dict)
        dev_result: BackendDevResult from Dev Agent
        iteration_count: Number of iterations to complete
        
    Returns:
        Dict matching BackendManifestEntry schema, or None on error
    """
    try:
        artifact_id = artifact.get("id", "unknown")
        kind = artifact.get("kind", "route")
        
        # Extract code paths from dev_result
        code_path = ""
        dependent_code_paths = []
        all_exports = []
        
        if dev_result:
            report = dev_result.get("report", {})
            if isinstance(report, dict):
                # New structure: current_state
                current_state = report.get("current_state", {})
                if isinstance(current_state, dict):
                    code_path = current_state.get("code_path", "")
                    dependent_code_paths = current_state.get("dependent_code_paths", [])
                    exports = current_state.get("exports", [])
                    if exports:
                        all_exports = exports if isinstance(exports, list) else [exports]
                
                # Fallback: files_changed (legacy)
                if not code_path:
                    files_changed = report.get("files_changed", [])
                    if files_changed:
                        first_file = files_changed[0] if isinstance(files_changed, list) else files_changed
                        if isinstance(first_file, dict):
                            code_path = first_file.get("path", "")
                        elif isinstance(first_file, str):
                            code_path = first_file
        
        # Get HTTP details from artifact
        http_path = artifact.get("http_path")
        http_method = artifact.get("http_method")
        
        # Get query params from artifact
        query_params = artifact.get("query_params")
        
        # Get expected_shape from artifact and convert to string reference
        response_shape = None
        expected_shape = artifact.get("expected_shape")
        if expected_shape:
            if isinstance(expected_shape, dict):
                shape_kind = expected_shape.get("kind", "object")
                response_shape = f"{shape_kind} response - see artifact spec"
            elif isinstance(expected_shape, str):
                response_shape = expected_shape
        
        # Build canonical query from artifact
        canonical_query = artifact.get("canonical_query")
        if canonical_query and isinstance(canonical_query, dict):
            canonical_query = json.dumps(canonical_query, separators=(",", ":"))
        
        entry = {
            "artifact_id": artifact_id,
            "kind": kind,
            "code_path": code_path,
            "dependent_code_paths": dependent_code_paths,
            "http_path": http_path,
            "http_method": http_method,
            "exports": all_exports,  # Include ALL exports from the file
            "query_params": query_params,
            "response_shape": response_shape,
            "canonical_query": canonical_query,
            "test_paths": [],  # No tester integration in dev-only flow
            "last_modified_at": datetime.utcnow().isoformat(),
            "iteration_count": iteration_count,
            "status": "success",
        }
        
        return entry
        
    except Exception as e:
        logger.warning(f"Error building manifest entry: {e}")
        return None


def _persist_manifest_entry(run_dir: str | Path, entry: dict[str, Any]) -> bool:
    """
    Persist a manifest entry to the backend_manifest.json file.
    
    Creates the manifest if it doesn't exist, or updates an existing entry
    if an entry with the same artifact_id exists.
    
    Args:
        run_dir: Path to the run directory
        entry: The BackendManifestEntry dict to persist
        
    Returns:
        True if successful, False otherwise
    """
    try:
        run_path = Path(run_dir)
        manifest_path = run_path / "dev" / "backend_manifest.json"
        
        # Ensure directory exists
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing manifest or create new
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        else:
            manifest = {
                "created_at": datetime.utcnow().isoformat(),
                "run_id": run_path.name,
                "entries": [],
            }
        
        # Ensure entries array exists
        if "entries" not in manifest:
            manifest["entries"] = []
        
        # Find existing entry by artifact_id and update, or append new
        artifact_id = entry["artifact_id"]
        found = False
        for i, existing in enumerate(manifest["entries"]):
            if existing.get("artifact_id") == artifact_id:
                manifest["entries"][i] = entry
                found = True
                logger.debug(f"Updated existing manifest entry: {artifact_id}")
                break
        
        if not found:
            manifest["entries"].append(entry)
            logger.debug(f"Added new manifest entry: {artifact_id}")
        
        # Write back
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)
        
        logger.info(f"Persisted manifest to {manifest_path}")
        return True
        
    except Exception as e:
        logger.exception(f"Failed to persist manifest entry: {e}")
        return False


# =============================================================================
# Helper functions
# =============================================================================

def _load_dashboard_concept(run_dir: str | Path) -> dict[str, Any] | None:
    """Load dashboard_concept.json from run directory."""
    run_path = Path(run_dir)
    concept_path = run_path / "planner" / "dashboard_concept.json"
    
    if not concept_path.exists():
        logger.debug(f"Dashboard concept not found at {concept_path}")
        return None
    
    try:
        with open(concept_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load dashboard concept: {e}")
        return None


def _lookup_metrics_ref(
    dashboard_concept: dict[str, Any] | None,
    metrics_ref: str | None,
) -> str:
    """
    Look up KPI/visual from dashboard_concept by metrics_ref.
    
    Patterns:
    - "kpi_<name>" → specific KPI
    - "v_<name>" → specific visual
    - "f_<name>" → specific filter
    - "kpis", "visuals", "filters" → entire section
    """
    if not metrics_ref:
        return "(no metrics_ref specified)"
    
    if not dashboard_concept:
        return f"(metrics_ref={metrics_ref}, but dashboard_concept not found)"
    
    try:
        # Check KPIs
        if metrics_ref.startswith("kpi_") or metrics_ref == "kpis":
            kpis = dashboard_concept.get("kpis", [])
            if metrics_ref == "kpis":
                return json.dumps(kpis, separators=(",", ":"))
            for kpi in kpis:
                if kpi.get("id") == metrics_ref or kpi.get("name") == metrics_ref.replace("kpi_", ""):
                    return json.dumps(kpi, separators=(",", ":"))
        
        # Check visuals
        if metrics_ref.startswith("v_") or metrics_ref == "visuals":
            visuals = dashboard_concept.get("visuals", dashboard_concept.get("charts", []))
            if metrics_ref == "visuals":
                return json.dumps(visuals, separators=(",", ":"))
            for visual in visuals:
                if visual.get("id") == metrics_ref or visual.get("name") == metrics_ref.replace("v_", ""):
                    return json.dumps(visual, separators=(",", ":"))
        
        # Check filters
        if metrics_ref.startswith("f_") or metrics_ref == "filters":
            filters = dashboard_concept.get("filters", [])
            if metrics_ref == "filters":
                return json.dumps(filters, separators=(",", ":"))
            for f in filters:
                if f.get("id") == metrics_ref or f.get("name") == metrics_ref.replace("f_", ""):
                    return json.dumps(f, separators=(",", ":"))
        
        # Direct key lookup
        if metrics_ref in dashboard_concept:
            return json.dumps(dashboard_concept[metrics_ref], separators=(",", ":"))
        
        return f"(metrics_ref={metrics_ref} not found)"
        
    except Exception as e:
        logger.warning(f"Error looking up metrics_ref {metrics_ref}: {e}")
        return f"(error: {metrics_ref})"


def _get_cleaned_data_files(run_dir: str | Path) -> list[str]:
    """Get list of cleaned data files from run directory."""
    run_path = Path(run_dir)
    cleaned_dir = run_path / "cleaned"
    
    if not cleaned_dir.exists():
        return []
    
    files = []
    for ext in ["*.csv", "*.parquet", "*.json", "*.xlsx"]:
        files.extend([f.name for f in cleaned_dir.glob(ext)])
    
    return files


__all__ = [
    # Callbacks for BackendDevLoopAgent (ADK built-in before/after_agent_callback)
    "before_loop_callback",
    "after_loop_callback",
    # State keys
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_PREVIOUS_SUMMARIES",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_METRICS_REF_CONTEXT",
    # Constants
    "SAMPLE_DASHBOARD_ROOT",
    "DEFAULT_TEST_RUN_DIR",
]
