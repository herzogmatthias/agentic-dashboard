from __future__ import annotations

from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# Query Parameters (LLM SHOULD fill these)
# ============================================================

class QueryParamSpec(BaseModel):
    """
    High-level conceptual definition of a query parameter for a route.
    The LLM fills these based on dashboard semantics.
    """
    name: str = Field(
        description="Name of the query parameter, e.g. 'income_category' or 'min_customers'."
    )
    type: Literal["string", "number", "boolean", "date", "enum"] = Field(
        default="string",
        description="Semantic type of the parameter."
    )
    required: bool = Field(
        default=False,
        description="Whether this parameter must be provided by the caller."
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable meaning of this parameter."
    )
    enum_values: Optional[List[str]] = Field(
        default=None,
        description="Only for type='enum'. List of allowed values."
    )
    default: Optional[Any] = Field(
        default=None,
        description="Conceptual default value, if applicable."
    )


# ============================================================
# Expected JSON Response Shape (LLM SHOULD fill these)
# ============================================================

class JsonFieldSpec(BaseModel):
    name: str = Field(description="Name of the field in the JSON response.")
    type: Literal["string", "number", "integer", "boolean", "object", "array"] = Field(
        description="High-level JSON type."
    )
    nullable: bool = Field(
        default=False,
        description="Whether this field may be null."
    )
    description: Optional[str] = Field(
        default=None,
        description="Explanation of the field's meaning."
    )


class ExpectedShape(BaseModel):
    """
    High-level output schema description.
    This is used by Test + QA generation.
    """
    kind: Literal["object", "array"] = Field(
        default="array",
        description="Whether the response is a single object or a list of objects."
    )
    fields: List[JsonFieldSpec] = Field(
        default_factory=list,
        description="For arrays: shape of each item. For objects: top-level fields."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional clarifying comments about the response shape."
    )


# ============================================================
# Artifact Status & Kind (NOT filled by LLM)
# ============================================================

class ArtifactOverallStatus(Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    failed = "failed"


class BackendArtifactKind(Enum):
    route = "route"
    helper = "helper"


# ============================================================
# PlannerArtifactTodo (LLM SHOULD fill all conceptual fields)
# ============================================================

class PlannerArtifactTodo(BaseModel):
    """
    One conceptual artifact in the backend todo list.
    LLM fills ONLY conceptual information:
    - id, kind, title, description
    - http_path, http_method
    - query_params
    - metrics_ref
    - expected_shape
    - canonical_query
    - depends_on, priority, tags

    System sets:
    - status, created_at, updated_at
    """

    # -------------------------------
    # Identity (LLM MUST fill)
    # -------------------------------
    id: str = Field(
        description="Unique identifier for the artifact, e.g. 'route_attrition_by_income'."
    )

    kind: BackendArtifactKind = Field(
        description="Whether this is a 'route' or a 'helper' artifact."
    )

    title: str = Field(
        description="Short human-readable name, e.g. 'Attrition by Income Category'."
    )

    description: Optional[str] = Field(
        default=None,
        description="Explanation of what this artifact does."
    )

    # -------------------------------
    # Route-specific contract (LLM SHOULD fill when kind='route')
    # -------------------------------
    http_path: Optional[str] = Field(
        default=None,
        description="HTTP path for the route, e.g. '/api/attrition/by-income'. Only for kind='route'."
    )

    http_method: Optional[Literal["GET", "POST", "PUT", "DELETE", "PATCH"]] = Field(
        default=None,
        description="HTTP method for this route. Use null for helpers, 'GET' for data routes."
    )

    query_params: Optional[List[QueryParamSpec]] = Field(
        default=None,
        description="List of conceptual query parameters accepted by this route."
    )

    metrics_ref: Optional[str] = Field(
        default=None,
        description="Reference to a valid dashboard_concept ID (kpi_*, v_*, f_*, or section key like 'kpis', 'visuals')."
    )

    expected_shape: Optional[ExpectedShape] = Field(
        default=None,
        description="Conceptual JSON response schema for this route."
    )

    canonical_query: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Representative example query used by test/QA agents."
    )

    # -------------------------------
    # Planning metadata (LLM SHOULD fill)
    # -------------------------------
    depends_on: List[str] = Field(
        default_factory=list,
        description="IDs of artifacts that must be completed first."
    )

    priority: int = Field(
        default=1,
        description="Planner priority: 1 = highest; larger numbers = lower priority."
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Optional list of domain-specific keywords."
    )

    # -------------------------------
    # System-maintained fields (NOT filled by LLM)
    # -------------------------------
    status: ArtifactOverallStatus = Field(
        default=ArtifactOverallStatus.pending,
        description="System-assigned status; LLM does not set this."
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this artifact entry was created. System-filled."
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this artifact entry was last updated. System-filled."
    )


# ============================================================
# PlannerTodoList (LLM SHOULD fill conceptual fields only)
# ============================================================

class PlannerTodoList(BaseModel):
    """
    The top-level todo list created by the backend planner.

    LLM SHOULD fill:
    - dashboard_goal
    - audience
    - artifacts (conceptual details only)

    System fills:
    - run_id, timestamps, statuses
    """

    run_id: str = Field(
        description="Unique run identifier. System-generated; NOT set by the LLM."
    )

    dataset_id: Optional[str] = Field(
        default=None,
        description="Identifier of the dataset being used. Typically system-filled."
    )

    dashboard_id: Optional[str] = Field(
        default=None,
        description="Identifier of the dashboard this backend supports. System-filled."
    )

    # High-level context (LLM SHOULD fill)
    dashboard_goal: Optional[str] = Field(
        default=None,
        description="High-level purpose of the dashboard, filled by the planner LLM."
    )

    audience: Optional[str] = Field(
        default=None,
        description="Who the dashboard is designed for, filled by the planner LLM."
    )

    # Artifacts to build (LLM MUST fill)
    artifacts: List[PlannerArtifactTodo] = Field(
        default_factory=list,
        description="List of conceptual backend artifacts required to implement the dashboard."
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this todo list was created. System-filled."
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this todo list was last updated. System-filled."
    )
