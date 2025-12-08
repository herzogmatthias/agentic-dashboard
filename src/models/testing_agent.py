"""
Testing Agent I/O schemas.

This module defines the input/output contracts for the Testing Agent,
which verifies backend implementations via automated tests.

The Testing Agent:
- Receives a PlannerArtifactTodo + DevReport context
- Writes/updates test files for the artifact
- Runs tests and captures results
- Emits a structured TestReport

The TestAgentResult is the agent's structured output schema.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from src.models.backend_planner_todos import PlannerArtifactTodo


# =============================================================================
# Test Report - Detailed Testing Report per Artifact
# =============================================================================

class TestReport(BaseModel):
    """
    Structured report of testing work done on a single artifact.
    
    This is the detailed output from the Testing Agent, capturing
    everything needed for retry decisions and manifest building.
    
    The manifest builder uses `current_tests` to populate `test_paths`
    in the BackendManifest.
    """
    
    artifact_id: str = Field(
        ...,
        description="ID of the artifact that was tested (from PlannerArtifactTodo.id)"
    )
    
    timestamp: str = Field(
        ...,
        description="ISO timestamp when this test iteration ran"
    )
    
    # -------------------------------------------------------------------------
    # Current state (used by manifest builder)
    # -------------------------------------------------------------------------
    
    current_tests: List[str] = Field(
        default_factory=list,
        description=(
            "All test file paths that currently cover this artifact, "
            "relative to workspace_root. Used by manifest builder for test_paths."
        )
    )
    
    # -------------------------------------------------------------------------
    # Delta for this iteration only
    # -------------------------------------------------------------------------
    
    test_files_created: List[str] = Field(
        default_factory=list,
        description="Test file paths created in this iteration, relative to workspace_root"
    )
    
    test_files_modified: List[str] = Field(
        default_factory=list,
        description="Test file paths modified in this iteration, relative to workspace_root"
    )
    
    test_files_deleted: List[str] = Field(
        default_factory=list,
        description="Test file paths deleted in this iteration (e.g., during refactoring)"
    )
    
    # -------------------------------------------------------------------------
    # Test execution results
    # -------------------------------------------------------------------------
    
    tests_run: int = Field(
        default=0,
        description="Number of tests executed for this artifact"
    )
    
    tests_failed: int = Field(
        default=0,
        description="Number of failing tests"
    )
    
    failed_test_names: List[str] = Field(
        default_factory=list,
        description="Identifiers or names of failing tests, if available"
    )
    
    # -------------------------------------------------------------------------
    # Execution context
    # -------------------------------------------------------------------------
    
    command_used: str = Field(
        default="npm test",
        description="The test command or script used, e.g. 'npm test -- <pattern>'"
    )
    
    output_snippet: Optional[str] = Field(
        default=None,
        description=(
            "Trimmed stdout/stderr snippet relevant to this artifact. "
            "Used for debugging failed tests. Should be truncated to ~500 chars."
        )
    )
    
    notes: Optional[str] = Field(
        default=None,
        description=(
            "Additional notes, e.g. limitations, skipped cases, "
            "or TODOs for future iterations"
        )
    )


# =============================================================================
# Test Agent Input - Input Contract
# =============================================================================

class TestAgentInput(BaseModel):
    """
    Input contract for the Testing Agent.
    
    Provided by the Loop Agent when invoking the Testing Agent
    to test a single artifact's implementation.
    """
    
    run_id: str = Field(
        ...,
        description="Current pipeline run ID; used for tracing and report naming"
    )
    
    artifact: PlannerArtifactTodo = Field(
        ...,
        description="Conceptual description of the backend artifact (route or helper)"
    )
    
    workspace_root: str = Field(
        ...,
        description="Filesystem root of the backend project, e.g. 'workspace/backend/'"
    )
    
    # -------------------------------------------------------------------------
    # Dev context
    # -------------------------------------------------------------------------
    
    dev_report_path: str = Field(
        ...,
        description=(
            "Path to the latest DevReport for this artifact, "
            "e.g. 'artifacts/backend/dev/<artifact_id>.dev_report.json'"
        )
    )
    
    # -------------------------------------------------------------------------
    # Optional context
    # -------------------------------------------------------------------------
    
    backend_manifest_path: Optional[str] = Field(
        default=None,
        description="Path to a previously built Backend Manifest (read-only, if available)"
    )
    
    test_report_dir: str = Field(
        default="artifacts/qa/tests",
        description="Directory (relative to workspace_root) where TestReports should be written"
    )
    
    # -------------------------------------------------------------------------
    # Hints from previous iterations
    # -------------------------------------------------------------------------
    
    previous_test_summary: Optional[str] = Field(
        default=None,
        description="Short summary from the last Test run, if this is a fix/refactor iteration"
    )
    
    previous_qa_summary: Optional[str] = Field(
        default=None,
        description="Short summary from the last QA run, useful when adapting tests to match expected behavior"
    )


# =============================================================================
# Test Agent Result - Structured Output Schema
# =============================================================================

class TestAgentResult(BaseModel):
    """
    Output contract for the Testing Agent.
    
    This is the agent's structured output schema (output_schema in LlmAgent).
    Contains control metadata for the artifact loop plus the detailed TestReport.
    
    The orchestrator uses `status`, `needs_dev_fix`, and `needs_spec_clarification`
    to determine the next step in the artifact loop:
    - success → proceed to QA (routes) or complete (helpers)
    - failed + needs_dev_fix → route back to Dev
    - failed + needs_spec_clarification → escalate to Planner
    - partial → treat as soft failure, may proceed with warning
    """
    
    run_id: str = Field(
        ...,
        description="Echo of the input run ID"
    )
    
    artifact_id: str = Field(
        ...,
        description="ID of the artifact this result belongs to"
    )
    
    status: Literal["success", "failed", "partial"] = Field(
        ...,
        description=(
            "Overall outcome of this Test iteration: "
            "'success' = tests written and passing, "
            "'failed' = tests failing or could not be executed, "
            "'partial' = tests added but coverage knowingly incomplete"
        )
    )
    
    summary: str = Field(
        ...,
        description="Short human-readable explanation of what tests were written/run and the outcome"
    )
    
    test_report: TestReport = Field(
        ...,
        description="Full structured TestReport for this artifact and iteration"
    )
    
    # -------------------------------------------------------------------------
    # Routing signals for artifact loop
    # -------------------------------------------------------------------------
    
    needs_dev_fix: bool = Field(
        default=False,
        description=(
            "True if failures appear to be due to implementation bugs. "
            "Dev Agent should fix the code."
        )
    )
    
    needs_spec_clarification: bool = Field(
        default=False,
        description=(
            "True if failures appear to come from ambiguous or insufficient specs. "
            "Planner may need to adjust the artifact definition."
        )
    )
    
    # -------------------------------------------------------------------------
    # Error details
    # -------------------------------------------------------------------------
    
    error_details: Optional[str] = Field(
        default=None,
        description=(
            "If tests could not be executed at all (e.g., syntax error in test file, "
            "npm test command failed), technical details go here"
        )
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Core models
    "TestReport",
    "TestAgentInput",
    "TestAgentResult",
    # Re-exported for convenience
    "PlannerArtifactTodo",
]
