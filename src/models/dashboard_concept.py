from __future__ import annotations

from pathlib import Path
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class DashboardMeta(BaseModel):
    """High-level metadata about the dashboard."""

    title: str = Field(
        ...,
        description="Short, user-facing dashboard title (e.g. 'Customer Attrition Overview').",
    )
    description: str = Field(
        ...,
        description="1–3 sentence description of the dashboard's purpose and scope.",
    )
    audience: str = Field(
        ...,
        description="Primary audience for the dashboard, e.g. 'manager', 'analyst', 'ops', or 'mixed'.",
    )
    primary_use_case: str = Field(
        ...,
        description="Main analytical use case, e.g. 'monitoring', 'exploration', or 'comparison'.",
    )


class KPI(BaseModel):
    """A key metric surfaced prominently on the dashboard."""

    id: str = Field(
        ...,
        description="Stable, machine-friendly identifier for the KPI (e.g. 'churn_rate').",
    )
    title: str = Field(
        ...,
        description="User-facing label for the KPI (e.g. 'Churn Rate').",
    )
    description: str = Field(
        ...,
        description="Short explanation of what the KPI measures and why it matters.",
    )
    formula: str = Field(
        ...,
        description="Human-readable definition (e.g. 'Attrited customers / All customers').",
    )
    time_context: str | None = Field(
        None,
        description="Optional time context (e.g. 'Last 30 days vs previous 30 days').",
    )
    format: str = Field(
        "float",
        description="Recommended display format: 'integer', 'float', 'currency', 'percentage', etc.",
    )


class Measure(BaseModel):
    """A numeric quantity plotted or summarized in a visual."""

    column_or_kpi: str = Field(
        ...,
        description="Name of the underlying column or KPI id used as the measure.",
    )
    aggregation: str = Field(
        "NONE",
        description="Aggregation applied when computing the measure (e.g. 'SUM', 'AVG', 'NONE').",
    )


class Dimension(BaseModel):
    """A grouping or categorization used in a visual."""

    column: str = Field(
        ...,
        description="Column used as the dimension (grouping or x-axis).",
    )
    time_granularity: str = Field(
        "none",
        description="If time-like, how it should be bucketed: 'day', 'week', 'month', etc.; otherwise 'none'.",
    )


class StaticFilter(BaseModel):
    """A fixed filter applied to a visual or metric."""

    column: str = Field(
        ...,
        description="Column the filter is applied to.",
    )
    operator: str = Field(
        ...,
        description="Operator such as '=', '!=', '>', '<=', 'in'.",
    )
    value: str = Field(
        ...,
        description="Filter value; encode lists or complex values as JSON string if needed.",
    )


class Visual(BaseModel):
    """
    A chart or table on the dashboard.

    'data_table' is intended for a row-level / detail table,
    whereas 'table' is typically for aggregated summaries.
    """

    id: str = Field(
        ...,
        description="Stable, machine-friendly identifier for the visual (e.g. 'churn_by_segment').",
    )
    title: str = Field(
        ...,
        description="User-facing title shown above the visual.",
    )
    purpose: str = Field(
        ...,
        description="Short description of the analytical question or insight this visual provides.",
    )
    type: str = Field(
        ...,
        description=(
            "Visual type, e.g. 'timeseries_line', 'bar', 'stacked_bar', 'column', "
            "'scatter', 'histogram', 'pie', 'heatmap', 'table', 'data_table'."
        ),
    )
    measures: List[Measure] = Field(
        ...,
        description="List of measures (numeric quantities) displayed in the visual.",
    )
    dimensions: List[Dimension] = Field(
        default_factory=list,
        description="Dimensions used for grouping, axes, or faceting.",
    )
    static_filters: List[StaticFilter] = Field(
        default_factory=list,
        description="Filters that are always applied to this visual.",
    )
    priority: str = Field(
        "supporting",
        description="Importance of this visual for layout decisions: 'hero', 'supporting', or 'optional'.",
    )
    table_columns: List[str] | None = Field(
        None,
        description=(
            "Optional list of column names to display when the visual is a table or data_table. "
            "If None, the UI chooses a sensible default set."
        ),
    )


class GlobalFilter(BaseModel):
    """A filter control that affects multiple visuals on the dashboard."""

    id: str = Field(
        ...,
        description="Stable identifier for the filter control.",
    )
    title: str = Field(
        ...,
        description="User-facing label for the filter (e.g. 'Income band').",
    )
    column: str = Field(
        ...,
        description="Underlying column that the filter controls.",
    )
    control_type: str = Field(
        ...,
        description=(
            "UI control type, e.g. 'dropdown', 'multi-select', 'searchable-select', "
            "'date-range', 'slider', or 'checkbox'."
        ),
    )
    multi: bool = Field(
        False,
        description="Whether the filter allows multiple selections.",
    )
    default: str | None = Field(
        None,
        description="Optional default value or selection for the filter (as a string).",
    )
    applies_to: List[str] = Field(
        default_factory=list,
        description=(
            "List of visual ids this filter should affect. "
            "Convention: empty list means 'applies to all visuals'."
        ),
    )


class DashboardConcept(BaseModel):
    """
    High-level design of a single-page dashboard that the UI Dev agent should implement.
    """

    meta: DashboardMeta = Field(
        ...,
        description="High-level metadata describing the dashboard.",
    )
    kpis: List[KPI] = Field(
        ...,
        description="Core KPIs that should be prominently displayed.",
    )
    visuals: List[Visual] = Field(
        ...,
        description="Charts and tables that make up the dashboard.",
    )
    global_filters: List[GlobalFilter] = Field(
        default_factory=list,
        description="Filter controls that apply across multiple visuals.",
    )
    layout_description: str = Field(
        ...,
        description=(
            "Free-text description of how to arrange KPIs, visuals, and filters on a single page "
            "(e.g. which elements go in the header, hero row, side-by-side, etc.)."
        ),
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Known data or design limitations that the UI Dev agent should be aware of.",
    )

