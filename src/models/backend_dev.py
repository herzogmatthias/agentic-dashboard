"""
Backend Dev Agent I/O schemas.

This module defines the input/output contracts for the Backend Dev Agent,
which processes individual PlannerArtifactTodo items and produces DevReports.

The BackendDevResult is the agent's structured output schema.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from src.models.backend_planner_todos import PlannerArtifactTodo, BackendArtifactKind


class BackendDevInput(BaseModel):
    """
    Input contract for the Backend Dev Agent.
    
    Provided by the Loop Agent when invoking the Backend Dev Agent
    to implement a single artifact.
    """
    
    run_id: str = Field(
        ...,
        description="Unique identifier for this pipeline run"
    )
    artifact: PlannerArtifactTodo = Field(
        ...,
        description="The artifact to implement (from Backend Planner)"
    )
    workspace_root: str = Field(
        ...,
        description="Absolute path to the sample-dashboard Next.js project"
    )
    previous_summaries: Optional[List[str]] = Field(
        default=None,
        description=(
            "Condensed summaries from prior artifact DevReports in this run. "
            "Helps agent understand what's already been created and avoid duplication."
        )
    )


# =============================================================================
# Backend Dev Result - Structured Output Schema
# =============================================================================

class BackendDevResult(BaseModel):
    """
    Output contract for the Backend Dev Agent.
    
    This is the agent's structured output schema (output_schema in LlmAgent).
    Contains a high-level status/summary plus the detailed DevReport.
    """
    
    status: Literal["success", "partial", "failed"] = Field(
        ...,
        description="Overall status of the dev work (mirrors DevReport.status)"
    )
    summary: str = Field(
        ...,
        description="Brief summary for the Loop Agent (1-2 sentences)"
    )
    escalate: bool = Field(
        default=False,
        description=(
            "Whether to escalate to the user. Set True for complexity issues "
            "(unclear requirements, artifact too complex) that need human input. "
            "Set False for technical issues that can be retried."
        )
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "BackendDevInput",
    "BackendDevResult",
    # Re-exported for convenience
    "PlannerArtifactTodo",
    "BackendArtifactKind",
]
