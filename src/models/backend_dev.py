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


# =============================================================================
# Current State and Changes - Structured tracking
# =============================================================================

class DevCurrentState(BaseModel):
    """
    Current state of the implementation after this iteration.
    
    Used by manifest builder and Testing Agent to understand what
    code exists and should be tested.
    """
    
    code_path: str = Field(
        ...,
        description="Primary file path for this artifact (e.g., 'src/app/api/sales/route.ts')"
    )
    
    dependent_code_paths: List[str] = Field(
        default_factory=list,
        description=(
            "Other files this implementation depends on or uses "
            "(e.g., helper modules, shared types)"
        )
    )
    
    exports: Optional[List[str]] = Field(
        default=None,
        description=(
            "Key exports from this artifact (function names, classes). "
            "Optional - useful for helpers that export reusable functions."
        )
    )


class DevChanges(BaseModel):
    """
    Delta of changes made in this iteration.
    
    Tracks what files were created, modified, or deleted during
    this iteration of artifact implementation.
    """
    
    files_created: List[str] = Field(
        default_factory=list,
        description="Files created in this iteration, relative to workspace_root"
    )
    
    files_modified: List[str] = Field(
        default_factory=list,
        description="Files modified in this iteration, relative to workspace_root"
    )
    
    files_deleted: List[str] = Field(
        default_factory=list,
        description="Files deleted in this iteration (e.g., during refactoring)"
    )


# =============================================================================
# Dev Report - Detailed Implementation Report
# =============================================================================

class DevReport(BaseModel):
    """
    Structured report of work done on a single artifact.
    
    This is the detailed output from the Backend Dev Agent, capturing
    everything needed for Tester/QA agents and manifest aggregation.
    
    Structure follows current_state + changes pattern:
    - current_state: DevCurrentState with code_path, dependent_code_paths, exports
    - changes: DevChanges with files_created, files_modified, files_deleted
    """
    
    artifact_id: str = Field(
        ...,
        description="ID of the artifact that was implemented (from PlannerArtifactTodo.id)"
    )
    artifact_type: Literal["route", "helper"] = Field(
        ...,
        description="Type of artifact (matches BackendArtifactKind)"
    )
    status: Literal["success", "partial", "failed"] = Field(
        ...,
        description=(
            "Overall status: "
            "'success' = fully implemented and validated, "
            "'partial' = implemented but validation issues, "
            "'failed' = could not implement"
        )
    )
    summary: str = Field(
        ...,
        description="Human-readable summary of what was done (2-3 sentences)"
    )
    
    # -------------------------------------------------------------------------
    # Current state (used by manifest builder and Tester)
    # -------------------------------------------------------------------------
    
    current_state: DevCurrentState = Field(
        ...,
        description="Current state of the implementation after this iteration"
    )
    
    # -------------------------------------------------------------------------
    # Delta for this iteration
    # -------------------------------------------------------------------------
    
    changes: DevChanges = Field(
        default_factory=DevChanges,
        description="Files created, modified, or deleted in this iteration"
    )
    
    # -------------------------------------------------------------------------
    # Implementation notes
    # -------------------------------------------------------------------------
    
    action_summary: str = Field(
        default="",
        description="Brief description of actions taken (e.g., 'Created route handler')"
    )
    
    implementation_notes: Optional[str] = Field(
        default=None,
        description="Notes about implementation decisions, trade-offs, or limitations"
    )
    
    next_steps: Optional[List[str]] = Field(
        default=None,
        description="Suggested next steps if status is 'partial' or for future iterations"
    )


# =============================================================================
# Backend Dev Input - Input Contract
# =============================================================================

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
    report: DevReport = Field(
        ...,
        description="Detailed structured report of the implementation"
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Current state and changes models
    "DevCurrentState",
    "DevChanges",
    # Core models
    "DevReport",
    "BackendDevInput",
    "BackendDevResult",
    # Re-exported for convenience
    "PlannerArtifactTodo",
    "BackendArtifactKind",
]
