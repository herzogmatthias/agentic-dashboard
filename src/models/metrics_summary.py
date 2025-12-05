from __future__ import annotations

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


# ---------------------------------------------------------------------------
# Helper models
# ---------------------------------------------------------------------------

class MetricValue(BaseModel):
    """
    A single scalar metric value.
    Example: {"name": "mean_credit_limit", "value": 8934.22, "description": "..."}.
    """
    name: str
    value: float
    description: Optional[str] = None


class SegmentMetric(BaseModel):
    """
    Metrics computed for segments/groups, e.g. attrition by income bracket,
    churn rate by card tier, sales by region.
    """
    segment_name: str = Field(
        ...,
        description="The dimension used for grouping, e.g. 'Income_Category'."
    )
    segment_value: str = Field(
        ...,
        description="The specific group value, e.g. '$40K - $60K'."
    )
    metrics: Dict[str, float] = Field(
        ...,
        description="Arbitrary metric names -> values for this segment."
    )
    sample_size: Optional[int] = Field(
        default=None,
        description="Number of records in this segment (if known)."
    )
    artifact_name: Optional[str] = Field(
        default=None,
        description="Logical name of the artifact."
    )


class CorrelationEntry(BaseModel):
    """
    Correlation between a numeric feature and a label/target variable.
    Can be extended later for mutual information, ANOVA, etc.
    """
    feature: str
    target: str
    coefficient: float = Field(..., description="Correlation coefficient (Pearson, unless noted).")
    magnitude_rank: Optional[int] = Field(
        default=None,
        description="Rank by absolute correlation magnitude, if computed."
    )


class Artifact(BaseModel):
    """
    Simple reference to an artifact generated during data analysis.
    """
    name: str = Field(..., description="Logical name of the artifact.")
    description: Optional[str] = None
    format: Optional[str] = None


# ---------------------------------------------------------------------------
# Main MetricsSummary
# ---------------------------------------------------------------------------

class MetricsSummary(BaseModel):
    """
    Generalized summary of programmatic metrics computed during analysis.

    Works for:
    - churn/attrition analysis
    - sales analytics
    - fraud scoring
    - HR attrition
    - manufacturing quality metrics
    - etc.

    The goal is to give the Analyzer & UI agents a compact, predictable
    structure without large blobs or dataset-specific assumptions.
    """

    dataset_name: Optional[str] = Field(
        default=None,
        description="Logical dataset name, e.g. 'bank_churn', 'sales_2024'."
    )

    # -------------------- Global metrics --------------------
    overall_metrics: List[MetricValue] = Field(
        default_factory=list,
        description="Top-level simple metrics (counts, rates, means, etc.)."
    )

    # -------------------- Segment metrics -------------------
    segment_metrics: List[SegmentMetric] = Field(
        default_factory=list,
        description=(
            "Metrics broken down by categories or segments "
            "e.g. churn by income bracket, sales by region."
        ),
    )

    # -------------------- Correlations ----------------------
    correlations: List[CorrelationEntry] = Field(
        default_factory=list,
        description="List of feature-target correlations for numeric features."
    )

    # -------------------- Files produced --------------------
    artifacts: List[Artifact] = Field(
        default_factory=list,
        description="Logical names of analysis artifacts (CSV/JSON) for downstream use."
    )

    # -------------------- Guidance for next agents ----------
    recommended_next_steps: List[str] = Field(
        default_factory=list,
        description="Short list of recommended analytical or modeling steps."
    )

    notes: List[str] = Field(
        default_factory=list,
        description="Free-form notes or caveats (kept small)."
    )
