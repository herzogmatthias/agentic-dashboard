"""
Shared utility functions for agents.

These are helper functions used by agent callbacks, not tools.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


def load_context_for_backend(run_dir: str | Path) -> dict[str, Any]:
    """
    Load dashboard_concept, data_profile, optionally metrics_summary, and cleaned_data_files for context injection.
    
    Returns minified JSON strings (no truncation - full content preserved).
    This is used by the before_model_callback to inject context into the prompt.
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        Dictionary with dashboard_concept, data_profile, optionally metrics_summary, and cleaned_data_files list
    """
    run_dir = Path(run_dir)
    context: dict[str, Any] = {}
    
    # Load dashboard concept
    dashboard_path = run_dir / "planner" / "dashboard_concept.json"
    if dashboard_path.exists():
        try:
            content = json.loads(dashboard_path.read_text(encoding="utf-8"))
            minified = json.dumps(content, separators=(",", ":"))
            context["dashboard_concept"] = minified
        except Exception as e:
            context["dashboard_concept_error"] = str(e)
    
    # Load data profile
    profile_path = run_dir / "data_profile.json"
    if profile_path.exists():
        try:
            content = json.loads(profile_path.read_text(encoding="utf-8"))
            minified = json.dumps(content, separators=(",", ":"))
            context["data_profile"] = minified
        except Exception as e:
            context["data_profile_error"] = str(e)
    
    # Load metrics summary (optional)
    metrics_path = run_dir / "metrics_summary.json"
    if metrics_path.exists():
        try:
            content = json.loads(metrics_path.read_text(encoding="utf-8"))
            minified = json.dumps(content, separators=(",", ":"))
            context["metrics_summary"] = minified
        except Exception as e:
            context["metrics_summary_error"] = str(e)
    
    # Load cleaned data files list
    cleaned_dir = run_dir / "cleaned"
    if cleaned_dir.exists():
        try:
            files = []
            for ext in ["*.csv", "*.parquet", "*.json", "*.xlsx"]:
                files.extend([f.name for f in cleaned_dir.glob(ext)])
            context["cleaned_data_files"] = sorted(files)
        except Exception as e:
            context["cleaned_data_files_error"] = str(e)
    else:
        context["cleaned_data_files"] = []
    
    return context
