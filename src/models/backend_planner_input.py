"""
Barebone input models for Backend Planner Agent tool.

These models exclude system fields (datetime, status) that ADK's automatic
function calling cannot parse. They are converted to the full models
(PlannerTodoList, PlannerArtifactTodo) in the tool function.
"""

from typing import Any, Optional, Literal

from pydantic import BaseModel, Field


class QueryParamInput(BaseModel):
    """Query parameter spec - mirrors QueryParamSpec without system fields."""
    name: str = Field(description="Name of the query parameter, e.g. 'income_category'")
    type: Literal["string", "number", "boolean", "date", "enum"] = Field(
        default="string", description="Semantic type of the parameter"
    )
    required: bool = Field(default=False, description="Whether this parameter must be provided")
    description: Optional[str] = Field(default=None, description="Human-readable meaning")
    enum_values: Optional[list[str]] = Field(default=None, description="Allowed values for type='enum'")
    default: Optional[Any] = Field(default=None, description="Default value if not provided")


class JsonFieldInput(BaseModel):
    """JSON field spec - mirrors JsonFieldSpec without system fields."""
    name: str = Field(description="Name of the field in the JSON response")
    type: Literal["string", "number", "integer", "boolean", "object", "array"] = Field(
        description="High-level JSON type"
    )
    nullable: bool = Field(default=False, description="Whether this field may be null")
    description: Optional[str] = Field(default=None, description="Explanation of the field's meaning")


class ExpectedShapeInput(BaseModel):
    """Expected response shape - mirrors ExpectedShape without system fields."""
    kind: Literal["object", "array"] = Field(
        default="array", description="Whether response is a single object or array"
    )
    fields: list[JsonFieldInput] = Field(
        default_factory=list, description="Shape of each item (array) or top-level fields (object)"
    )
    notes: Optional[str] = Field(default=None, description="Optional clarifying comments")


class ArtifactInput(BaseModel):
    """
    Barebone artifact input - no system fields (status, created_at, updated_at).
    
    Mirrors PlannerArtifactTodo but excludes fields that ADK cannot parse.
    """
    id: str = Field(description="Unique identifier, e.g. 'route_sales_by_category'")
    kind: Literal["route", "helper"] = Field(description="'route' or 'helper'")
    title: str = Field(description="Short human-readable name")
    description: Optional[str] = Field(default=None, description="What this artifact does")
    
    # Route-specific (optional) - set http_method=null for helpers
    http_path: Optional[str] = Field(default=None, description="HTTP path, e.g. '/api/sales'")
    http_method: Optional[Literal["GET", "POST", "PUT", "DELETE", "PATCH"]] = Field(
        default=None, description="HTTP method. Use null for helpers, 'GET' for data routes."
    )
    query_params: Optional[list[QueryParamInput]] = Field(default=None, description="Query parameters")
    metrics_ref: Optional[str] = Field(default=None, description="Reference to metrics block")
    expected_shape: Optional[ExpectedShapeInput] = Field(default=None, description="Expected JSON response shape")
    canonical_query: Optional[dict[str, Any]] = Field(default=None, description="Example query for testing")
    
    # Planning metadata
    depends_on: list[str] = Field(default_factory=list, description="IDs of dependencies")
    priority: int = Field(default=1, description="1 = highest priority")
    tags: list[str] = Field(default_factory=list, description="Domain keywords")


class TodoListInput(BaseModel):
    """
    Barebone todo list input - no system fields (run_id, created_at, updated_at).
    
    Mirrors PlannerTodoList but excludes fields that ADK cannot parse.
    """
    dashboard_goal: str = Field(description="High-level purpose of the dashboard")
    audience: str = Field(description="Who the dashboard is designed for")
    artifacts: list[ArtifactInput] = Field(description="List of artifacts to build")
