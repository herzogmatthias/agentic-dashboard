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
# File Change Tracking
# =============================================================================

class FileChange(BaseModel):
    """
    Record of a file created or modified by the Backend Dev Agent.
    
    Tracks what files were touched during artifact implementation,
    enabling the Tester and QA agents to understand what to validate.
    """
    
    path: str = Field(
        ...,
        description="Relative path from workspace_root (e.g., 'src/app/api/sales/route.ts')"
    )
    action: Literal["created", "modified"] = Field(
        ...,
        description="Whether the file was newly created or modified"
    )
    description: str = Field(
        ...,
        description="Brief description of what this file does or what changed"
    )


# =============================================================================
# Dev Report - Detailed Implementation Report
# =============================================================================

class DevReport(BaseModel):
    """
    Structured report of work done on a single artifact.
    
    This is the detailed output from the Backend Dev Agent, capturing
    everything needed for Tester/QA agents and manifest aggregation.
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
    files_changed: List[FileChange] = Field(
        default_factory=list,
        description="List of files created or modified during implementation"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other artifact IDs this implementation depends on (discovered during dev)"
    )
    lint_passed: bool = Field(
        ...,
        description="Whether npm lint passed for created/modified files"
    )
    type_check_passed: bool = Field(
        ...,
        description="Whether TypeScript type-check passed for created/modified files"
    )
    errors: Optional[List[str]] = Field(
        default=None,
        description="Error messages if status is 'partial' or 'failed'"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this report was generated"
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
    # Core models
    "FileChange",
    "DevReport",
    "BackendDevInput",
    "BackendDevResult",
    # Re-exported for convenience
    "PlannerArtifactTodo",
    "BackendArtifactKind",
]
