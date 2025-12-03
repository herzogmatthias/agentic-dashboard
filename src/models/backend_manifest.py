"""Pydantic schemas for Backend Agent outputs.

This module defines the data models used by the Backend Agent to track
created API routes, TypeScript models, and validation results.
"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# TypeScript Interface Constants (for reference in prompts)
# =============================================================================

API_ERROR_TYPESCRIPT = '''
/**
 * Standard error response format for all API routes.
 * Use this interface for consistent error handling across the dashboard.
 */
interface ApiError {
  error: {
    code: string;        // e.g., "INVALID_FILTER", "DATA_NOT_FOUND", "INTERNAL_ERROR"
    message: string;     // Human-readable error message
    details?: unknown;   // Optional additional context (e.g., validation errors)
  };
}

// HTTP Status Codes:
// - 400: Client errors (invalid parameters, missing required fields)
// - 404: Resource not found
// - 500: Server/internal errors
'''.strip()


# =============================================================================
# Data Source Schema
# =============================================================================

class DataSourceInfo(BaseModel):
    """Information about the data source used by API routes.
    
    Tracks the original cleaned CSV location and where it was copied
    in the Next.js project.
    """
    
    original_path: str = Field(
        ...,
        description="Path to cleaned CSV in run artifacts (e.g., '{run_dir}/data_analysis/cleaned/data.csv')"
    )
    project_path: str = Field(
        ...,
        description="Path where CSV was copied in sample-dashboard (e.g., 'data/cleaned.csv')"
    )
    row_count: int = Field(
        ...,
        ge=0,
        description="Number of rows in the dataset"
    )
    columns: List[str] = Field(
        ...,
        description="List of column names in the dataset"
    )


# =============================================================================
# Model Schema
# =============================================================================

class ModelInfo(BaseModel):
    """Information about a created TypeScript model/type file.
    
    Tracks TypeScript interfaces and types created for API responses.
    """
    
    name: str = Field(
        ...,
        description="Model name (e.g., 'AttritionData', 'KpiResponse')"
    )
    file_path: str = Field(
        ...,
        description="Relative path to the model file (e.g., 'models/AttritionData.ts')"
    )
    description: str = Field(
        ...,
        description="Brief description of what this model represents"
    )
    exports: List[str] = Field(
        ...,
        min_length=1,
        description="List of exported type/interface names from this file"
    )


# =============================================================================
# Query Parameter Schema
# =============================================================================

class QueryParam(BaseModel):
    """Definition of an API route query parameter.
    
    Used to document the query parameters accepted by each API route
    for filtering and customization.
    """
    
    name: str = Field(
        ...,
        description="Parameter name as it appears in the URL (e.g., 'income_category')"
    )
    type: str = Field(
        ...,
        description="TypeScript type of the parameter (e.g., 'string', 'number', 'string[]')"
    )
    required: bool = Field(
        default=False,
        description="Whether this parameter is required for the request"
    )
    description: str = Field(
        ...,
        description="Description of what this parameter filters or controls"
    )


# =============================================================================
# Route Schema
# =============================================================================

class HttpMethod(str, Enum):
    """HTTP methods supported by API routes."""
    GET = "GET"
    POST = "POST"


class RouteInfo(BaseModel):
    """Information about a created API route.
    
    Tracks the API endpoints created by the Backend Agent, including
    their paths, methods, and relationships to dashboard visuals.
    """
    
    path: str = Field(
        ...,
        description="API route path (e.g., '/api/kpis/attrition-rate')"
    )
    file_path: str = Field(
        ...,
        description="Relative path to route file (e.g., 'app/api/kpis/attrition-rate/route.ts')"
    )
    method: Literal["GET", "POST"] = Field(
        default="GET",
        description="HTTP method for this route"
    )
    description: str = Field(
        ...,
        description="Brief description of what this route returns"
    )
    serves_visual_ids: List[str] = Field(
        default_factory=list,
        description="IDs from dashboard_concept.json that this route serves (e.g., ['kpi_1', 'v1'])"
    )
    query_params: Optional[List[QueryParam]] = Field(
        default=None,
        description="Query parameters accepted by this route"
    )
    response_schema: str = Field(
        ...,
        description="Reference to response type (e.g., 'AttritionRateResponse') or inline type description"
    )


# =============================================================================
# Validation Result Schema
# =============================================================================

class ValidationResult(BaseModel):
    """Results from running lint and build validation.
    
    Tracks whether the generated code passes validation and any errors encountered.
    """
    
    lint_passed: bool = Field(
        ...,
        description="Whether 'npm run lint' passed successfully"
    )
    build_passed: bool = Field(
        ...,
        description="Whether 'npm run build' passed successfully"
    )
    errors: Optional[List[str]] = Field(
        default=None,
        description="List of error messages if validation failed"
    )


# =============================================================================
# Backend Manifest Schema
# =============================================================================

class BackendManifest(BaseModel):
    """Complete manifest documenting all Backend Agent outputs.
    
    This manifest is written to {run_dir}/dev/backend_manifest.json and serves
    as the contract between the Backend Agent and Frontend Agent. It documents
    all created API routes, models, and validation status.
    """
    
    created_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when this manifest was created (auto-populated if not provided)"
    )
    run_id: str = Field(
        ...,
        description="Reference to the run directory (e.g., 'run_20251202_120000')"
    )
    data_source: DataSourceInfo = Field(
        ...,
        description="Information about the data source used by API routes"
    )
    models: List[ModelInfo] = Field(
        default_factory=list,
        description="List of TypeScript model files created"
    )
    routes: List[RouteInfo] = Field(
        default_factory=list,
        description="List of API routes created"
    )
    validation: ValidationResult = Field(
        ...,
        description="Results from lint and build validation"
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Important notes for Frontend/QA agents (e.g., known limitations, TODOs)"
    )
# =============================================================================
# Backend Status Enum
# =============================================================================

class BackendStatus(str, Enum):
    """Status of the Backend Agent's work."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# =============================================================================
# API Error Schema (Python representation)
# =============================================================================

class ApiError(BaseModel):
    """Python representation of the ApiError interface.
    
    Used for validation and documentation purposes. The actual TypeScript
    interface is defined in API_ERROR_TYPESCRIPT constant.
    """
    
    code: str = Field(
        ...,
        description="Error code (e.g., 'INVALID_FILTER', 'DATA_NOT_FOUND')"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[dict] = Field(
        default=None,
        description="Optional additional context"
    )
