from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum


# ---------------------------------------------------------------------------
# Small helper models
# ---------------------------------------------------------------------------

class Shape(BaseModel):
    rows: int = Field(..., description="Number of rows.")
    columns: int = Field(..., description="Number of columns.")


class LabelDefinition(BaseModel):
    """
    How the target/label was defined (e.g., churn_flag from Attrition_Flag).
    """
    label_column: str = Field(..., description="Name of the label column in the cleaned dataset.")
    source_column: Optional[str] = Field(
        default=None,
        description="Optional name of the original source column, e.g. 'Attrition_Flag'.",
    )
    positive_class: Optional[str] = Field(
        default=None,
        description="Value representing the positive class, e.g. '1' or 'Attrited Customer'.",
    )
    negative_class: Optional[str] = Field(
        default=None,
        description="Value representing the negative class, e.g. '0' or 'Existing Customer'.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Short explanation of the label definition and rationale.",
    )


class PiiAction(str, Enum):
    RETAINED = "retained"
    DROPPED = "dropped"
    MASKED = "masked"


class PiiNote(BaseModel):
    """
    Simple per-column PII handling note.
    """
    column: str
    action: PiiAction
    note: Optional[str] = None


class FileArtifact(BaseModel):
    """
    File produced by the cleaning step.
    """
    path: str = Field(..., description="Relative path inside the run workspace.")
    purpose: str = Field(..., description="Short description, e.g. 'canonical cleaned dataset'.")
    format: Optional[str] = Field(
        default=None,
        description="Optional format hint, e.g. 'csv', 'parquet'.",
    )


# ---------------------------------------------------------------------------
# Main CleaningSummary
# ---------------------------------------------------------------------------

class CleaningSummary(BaseModel):
    """
    Compact, structured summary of cleaning & preprocessing steps.

    Designed to replace the free-form markdown summary and be safe to send as a
    Google ADK function result.
    """

    dataset_name: Optional[str] = Field(
        default=None,
        description="Logical dataset name, e.g. 'bank_churn'.",
    )

    # Shapes before/after cleaning
    original_shape: Shape = Field(
        ...,
        description="Shape of the raw dataset that was loaded.",
    )
    cleaned_shape: Shape = Field(
        ...,
        description="Shape of the canonical cleaned dataset (e.g., cleaned.csv).",
    )

    # Column-level changes (kept very small / symbolic)
    dropped_columns: List[str] = Field(
        default_factory=list,
        description="Columns removed entirely during cleaning.",
    )
    transformed_columns: Dict[str, List[str]] = Field(
        default_factory=dict,
        description=(
            "Map of column name -> list of short operation tags, e.g. "
            "{'Income_Category': ['normalized', 'parsed_numeric_segment']}."
        ),
    )

    # Target / label definition (optional, but very useful)
    label_definition: Optional[LabelDefinition] = Field(
        default=None,
        description="Definition of the main label/target column, if any.",
    )
    imputation_summary: Optional[str] = Field(
        default=None,
        description=(
            "Short description of imputation strategy, if any. "
            "Example: 'Median imputation for numeric features in modeling only; "
            "no imputation in cleaned.csv'."
        ),
    )

    # PII / privacy
    pii_notes: List[PiiNote] = Field(
        default_factory=list,
        description="Per-column notes for PII handling.",
    )

    # Files written by the cleaning step
    files_produced: List[FileArtifact] = Field(
        default_factory=list,
        description="List of key artifacts produced (e.g., cleaned.csv, metrics summary files).",
    )

    # Free-form but short notes for agents/UI
    key_decisions: List[str] = Field(
        default_factory=list,
        description=(
            "Short bullet-style notes on important decisions, "
            "e.g. 'No date columns found; time-window churn not computed'."
        ),
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions that may affect analysis, e.g. label correctness, stationarity.",
    )
