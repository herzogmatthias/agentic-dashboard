from pydantic import BaseModel, Field
from typing import List, Optional


class PlannerMetadata(BaseModel):
    """
    Metadata about the planned dashboard returned by the Planner Agent.
    
    This provides a quick summary of key dashboard characteristics without
    requiring the orchestrator to parse the full dashboard spec JSON.
    """
    
    primary_goal: str = Field(
        ...,
        description="High-level goal of the dashboard (e.g., 'Monitor customer attrition')."
    )
    
    notable_segments: List[str] = Field(
        default_factory=list,
        description=(
            "List of notable data segments or cohorts identified during planning "
            "(e.g., 'High balance, low activity', 'New customers < 6 months')."
        )
    )
    
    visual_count: int = Field(
        ...,
        description="Total number of visuals (charts/tables) included in the dashboard plan."
    )
    
    kpi_count: int = Field(
        ...,
        description="Total number of KPIs included in the dashboard plan."
    )
    
    has_time_series: bool = Field(
        False,
        description="Whether the dashboard includes any time-series visualizations."
    )
    
    complexity: str = Field(
        "medium",
        description=(
            "Overall complexity assessment of the dashboard: 'simple', 'medium', or 'complex'. "
            "Based on number of visuals, filters, and data relationships."
        )
    )


class PlannerOutput(BaseModel):
    """
    Final structured output returned by the Planner Agent.
    
    This object is ALWAYS returned as the final JSON payload from the Planner.
    The orchestrator uses this to determine next steps: finish, clarify, or request more analysis.
    
    """
    
    needs_additional_analysis: Optional[List[str]] = Field(
        None,
        description=(
            "Optional list of additional analyses that the Data Analysis Agent should perform "
            "to improve the dashboard. Each item is a clear, actionable request "
            "(e.g., 'Calculate customer lifetime value segmented by income band', "
            "'Compute correlation matrix for numeric features'). "
            "Set to None or empty list if no additional analysis is needed."
        )
    )
    
    needs_user_clarification: Optional[List[str]] = Field(
        None,
        description=(
            "Optional list of questions for the user that would help refine the dashboard. "
            "Each item is a user-facing question "
            "(e.g., 'Should we prioritize time-based trends or segment comparisons?', "
            "'Do you want to focus on active customers only or include all?'). "
            "Set to None or empty list if no clarification is needed."
        )
    )
    
    meta: PlannerMetadata = Field(
        ...,
        description=(
            "Metadata about the dashboard plan, providing a quick summary of key characteristics."
        )
    )
    
    summary: str = Field(
        ...,
        description=(
            "Brief textual summary of the dashboard plan (2-4 sentences) describing "
            "the main purpose, key visuals, and audience. This is used by the orchestrator "
            "for generating the final user-facing summary."
        )
    )
