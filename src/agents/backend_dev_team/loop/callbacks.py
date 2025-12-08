"""
Loop Agent callbacks and state initialization helpers.

State initialization for the Dev Agent happens ONCE at the start of the
Loop Agent's _run_async_impl, not on every Dev Agent invocation.
"""

import json
from pathlib import Path
from typing import Any

from src.core.logging import get_logger
from src.agents.backend_dev_team.loop.tools import (
    STATE_KEY_RUN_DIR,
)

logger = get_logger(__name__)


# =============================================================================
# State Keys for Dev Agent
# =============================================================================

STATE_KEY_WORKSPACE_ROOT = "workspace_root"
STATE_KEY_PREVIOUS_SUMMARIES = "previous_summaries"
STATE_KEY_CLEANED_DATA_FILES = "cleaned_data_files"
STATE_KEY_METRICS_REF_CONTEXT = "metrics_ref_context"

# Default sample-dashboard root (relative to project)
SAMPLE_DASHBOARD_ROOT = Path(__file__).parent.parent.parent.parent.parent / "sample-dashboard"


# =============================================================================
# State initialization (called ONCE at start of Loop)
# =============================================================================

def initialize_dev_state(state: dict[str, Any], artifact: dict[str, Any]) -> None:
    """
    Initialize state for the Dev Agent before the loop starts.
    
    Called ONCE at the start of BackendDevLoopAgent._run_async_impl.
    Sets up:
    - workspace_root: Path to sample-dashboard project
    - metrics_ref_context: KPI/visual spec from dashboard_concept
    - cleaned_data_files: List of available data files
    - previous_summaries: Initialize if not present
    
    Args:
        state: Session state dict (mutable)
        artifact: The artifact being processed
    """
    artifact_id = artifact.get("id", "unknown")
    
    # Set workspace_root
    if STATE_KEY_WORKSPACE_ROOT not in state:
        state[STATE_KEY_WORKSPACE_ROOT] = str(SAMPLE_DASHBOARD_ROOT.resolve())
    
    # Look up metrics_ref context from dashboard_concept
    run_dir = state.get(STATE_KEY_RUN_DIR)
    metrics_ref = artifact.get("metrics_ref")
    
    if run_dir:
        dashboard_concept = _load_dashboard_concept(run_dir)
        state[STATE_KEY_METRICS_REF_CONTEXT] = _lookup_metrics_ref(dashboard_concept, metrics_ref)
        state[STATE_KEY_CLEANED_DATA_FILES] = _get_cleaned_data_files(run_dir)
    else:
        state[STATE_KEY_METRICS_REF_CONTEXT] = "(no run_dir in state)"
        state[STATE_KEY_CLEANED_DATA_FILES] = []
    
    # Initialize previous_summaries if not present
    if STATE_KEY_PREVIOUS_SUMMARIES not in state:
        state[STATE_KEY_PREVIOUS_SUMMARIES] = []
    
    logger.info(
        f"Dev state initialized for {artifact_id}",
        extra={
            "agent": "loop",
            "artifact_id": artifact_id,
            "metrics_ref": metrics_ref,
            "workspace_root": state.get(STATE_KEY_WORKSPACE_ROOT),
            "cleaned_files_count": len(state.get(STATE_KEY_CLEANED_DATA_FILES, [])),
        }
    )


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
    for ext in ["*.csv", "*.parquet"]:
        files.extend([f.name for f in cleaned_dir.glob(ext)])
    
    return files


__all__ = [
    "initialize_dev_state",
    "STATE_KEY_WORKSPACE_ROOT",
    "STATE_KEY_PREVIOUS_SUMMARIES",
    "STATE_KEY_CLEANED_DATA_FILES",
    "STATE_KEY_METRICS_REF_CONTEXT",
    "SAMPLE_DASHBOARD_ROOT",
]
