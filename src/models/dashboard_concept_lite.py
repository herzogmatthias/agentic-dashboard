from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


# ---------- Simple, tool-safe models (no Union / Optional) ----------

class KpiSpec(BaseModel):
    """A key metric to show prominently on the dashboard."""

    id: str = Field(
        ...,
        description="Stable machine-friendly identifier for the KPI (e.g. 'churn_rate').",
    )
    title: str = Field(
        ...,
        description="User-facing label for the KPI (e.g. 'Churn rate').",
    )
    description: str = Field(
        ...,
        description="Short explanation of what the KPI measures and why it matters.",
    )
    formula: str = Field(
        ...,
        description="Human-readable formula or definition (e.g. 'Attrited customers / All customers').",
    )
    time_context: str = Field(
        "",
        description=(
            "Time context for the KPI (e.g. 'Last 30 days vs previous 30 days'). "
            "Use empty string if no specific time context."
        ),
    )
    format: str = Field(
        "float",
        description=(
            "Recommended display format for the KPI, e.g. 'integer', 'float', "
            "'currency', 'percentage', 'duration'."
        ),
    )


class MeasureSpec(BaseModel):
    """A numeric quantity plotted or summarized in a visual."""

    column_or_kpi: str = Field(
        ...,
        description="Name of the underlying column or KPI id used as the measure.",
    )
    aggregation: str = Field(
        "NONE",
        description=(
            "Aggregation applied when computing the measure, e.g. 'SUM', 'AVG', "
            "'COUNT', 'COUNT_DISTINCT', 'MIN', 'MAX', or 'NONE'."
        ),
    )


class DimensionSpec(BaseModel):
    """A grouping or categorization used in a visual (e.g. x-axis or series)."""

    column: str = Field(
        ...,
        description="Column used as the dimension for grouping or x-axis.",
    )
    time_granularity: str = Field(
        "none",
        description=(
            "If the column is time-like, how it should be bucketed: "
            "'day', 'week', 'month', 'quarter', 'year'; otherwise 'none'."
        ),
    )


class StaticFilterSpec(BaseModel):
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
        description=(
            "Filter value as a string. If you need multiple values, encode them "
            "as a comma-separated string or JSON string."
        ),
    )


class VisualSpec(BaseModel):
    """
    A chart or table on the dashboard.

    'data_table' is intended for row-level / detail tables,
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
            "'scatter', 'histogram', 'pie', 'heatmap', 'table', or 'data_table'."
        ),
    )
    measures: List[MeasureSpec] = Field(
        ...,
        description="List of measures (numeric quantities) displayed in the visual.",
    )
    dimensions: List[DimensionSpec] = Field(
        default_factory=list,
        description="Dimensions used for grouping, axes, or faceting.",
    )
    static_filters: List[StaticFilterSpec] = Field(
        default_factory=list,
        description="Filters that are always applied to this visual.",
    )
    priority: str = Field(
        "supporting",
        description="Importance of this visual: 'hero', 'supporting', or 'optional'.",
    )
    table_columns: List[str] = Field(
        default_factory=list,
        description=(
            "Optional list of column names to display when the visual is a table or data_table. "
            "If empty, the UI layer should choose sensible defaults."
        ),
    )


class GlobalFilterSpec(BaseModel):
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
    default: str = Field(
        "",
        description=(
            "Default value or selection for the filter, as a string. "
            "Use empty string if there is no default."
        ),
    )
    applies_to: List[str] = Field(
        default_factory=list,
        description=(
            "List of visual ids that this filter should affect. "
            "If empty, the filter applies to all visuals."
        ),
    )


class DashboardConceptLite(BaseModel):
    """
    Simplified, tool-safe dashboard concept that the Planner Agent should produce.

    This is the schema that will be written to artifacts/planner/dashboard_concept.json
    and consumed by the UI Dev agent.
    """

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
    layout_description: str = Field(
        ...,
        description=(
            "Free-text description of how to arrange KPIs, visuals, and filters on the single page "
            "(e.g. which elements go in the header, hero KPIs row, side-by-side charts, etc.)."
        ),
    )
    kpis: List[KpiSpec] = Field(
        default_factory=list,
        description="List of key KPIs that should be prominently displayed on the dashboard.",
    )
    visuals: List[VisualSpec] = Field(
        default_factory=list,
        description="List of charts and tables that make up the dashboard.",
    )
    global_filters: List[GlobalFilterSpec] = Field(
        default_factory=list,
        description="Global filter controls that apply across multiple visuals.",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Known data or design limitations that consumers of the dashboard should be aware of.",
    )