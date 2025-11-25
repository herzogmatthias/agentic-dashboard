from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.core.config import RUNS_DIR


class DatasetState(BaseModel):
    """Paths for the dataset as it moves through the pipeline."""

    raw_path: Optional[str] = Field(
        default=None,
        description="Original dataset location (host path or upload handle).",
    )
    cleaned_path: Optional[str] = Field(
        default=None,
        description="Path to the cleaned dataset produced by the data agent.",
    )


class AnalysisOutputs(BaseModel):
    """Artifacts produced by the data analysis agent."""

    data_profile_path: Optional[str] = Field(
        default=None, description="Path to DataProfile markdown."
    )
    cleaning_summary_path: Optional[str] = Field(
        default=None, description="Path to CleaningSummary markdown."
    )
    stats_path: Optional[str] = Field(
        default=None,
        description="Optional path for serialized stats (e.g., dtype map, distributions).",
    )


class PlannerOutputs(BaseModel):
    """Artifacts produced by the planner agent."""

    dashboard_json_path: Optional[str] = Field(
        default=None, description="Path to the generated dashboard.json concept."
    )


class SharedSessionState(BaseModel):
    """
    Shared session state persisted in Google ADK sessions.

    Stores the per-run entry point (run_dir) plus downstream artifacts so the
    orchestrator and subagents can read/write consistently.
    """

    run_id: str = Field(..., description="Unique run identifier (e.g., run_20250101_120000).")
    run_dir: str = Field(..., description="Host path where all artifacts for the run are stored.")
    dataset: DatasetState = Field(default_factory=DatasetState)
    analysis: AnalysisOutputs = Field(default_factory=AnalysisOutputs)
    planner: PlannerOutputs = Field(default_factory=PlannerOutputs)
    pipeline_status: str = Field(
        default="initialized",
        description="High-level pipeline status marker (init, analysis_pending, planning_pending, complete, etc.).",
    )

    @classmethod
    def bootstrap(cls, run_id: str, run_dir: Path) -> "SharedSessionState":
        """Create an initial state with the run identifiers wired in."""
        return cls(run_id=run_id, run_dir=str(run_dir))




def _bootstrap_run_directory() -> tuple[str, Path]:
    """
    Create a per-run directory under runs/ and return (run_id, run_dir).
    This path is the shared entry point for artifacts copied from Daytona.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_id, run_dir