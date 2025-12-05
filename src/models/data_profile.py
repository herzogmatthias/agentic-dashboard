from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ColumnRole(str, Enum):
    """Logical role of a column in the dataset."""
    IDENTIFIER = "identifier"
    TARGET = "target"
    FEATURE = "feature"
    DATE = "date"
    META = "meta"
    UNKNOWN = "unknown"


class ColumnSourceType(str, Enum):
    CSV = "csv"
    SQL = "sql"
    OTHER = "other"

class SemanticType(str, Enum):
    """Semantic data type for downstream reasoning."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEXT = "text"
    BOOLEAN = "boolean"
    DATE = "date"
    IDENTIFIER = "identifier"
    LABEL = "label"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

class DatasetOverview(BaseModel):
    row_count: int = Field(..., description="Number of rows in the cleaned dataset.")
    column_count_raw: int = Field(..., description="Number of columns in the raw input.")
    column_count_clean: int = Field(..., description="Number of columns in the cleaned output.")
    new_columns: List[str] = Field(
        default_factory=list,
        description="Columns created during cleaning/feature engineering.",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Free-form notes about the dataset (short, bullet-style).",
    )


class NumericSummary(BaseModel):
    """Lightweight summary for numeric columns (optional)."""
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    outlier_flag: Optional[bool] = Field(
        default=None,
        description="True if column appears to have heavy tails / outliers.",
    )




class ColumnOrigin(BaseModel):
    """
    Where this column came from. Keeps multi-source support cheap.
    """
    source_type: ColumnSourceType = ColumnSourceType.CSV
    source_name: str = Field(
        ...,
        description="File name for CSV or table name for SQL, e.g. 'customers.csv' or 'public.customers'.",
    )
    logical_table: Optional[str] = Field(
        default=None,
        description="Optional logical name (e.g. 'customers'); purely for human/agent convenience.",
    )

class ColumnProfile(BaseModel):
    """
    COMPACT per-column profile.

    Only produced for 'key' columns, not for every column in the dataset.
    The Data Agent decides which columns are 'key' (e.g., target, identifier,
    dates, and top N important features).
    """
    name: str = Field(..., description="Column name in the cleaned dataset.")
    role: ColumnRole = Field(
        ColumnRole.UNKNOWN,
        description="Logical role in modeling / analysis.",
    )
    semantic_type: SemanticType = Field(
        SemanticType.UNKNOWN,
        description="Semantic category (numeric, categorical, date, etc.).",
    )

    dtype_raw: Optional[str] = Field(
        default=None,
        description="Original dtype as read from raw data.",
    )
    dtype_clean: Optional[str] = Field(
        default=None,
        description="Dtype after cleaning / casting.",
    )

    missing_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of missing values in this column.",
    )
    unique_count: Optional[int] = Field(
        default=None,
        description="Number of distinct values (may be skipped for very large columns).",
    )

    example_values: List[str] = Field(
        default_factory=list,
        description="A few representative values as strings (for UI previews).",
    )

    numeric_summary: Optional[NumericSummary] = Field(
        default=None,
        description="Present only for numeric-like columns.",
    )

    selection_reason: Optional[str] = Field(
        default=None,
        description="Why this column is included as a 'key' column (e.g., 'primary label', 'top_1_feature_importance', 'identifier').",
    )
    
    origin: Optional[ColumnOrigin] = Field(
        default=None,
        description=(
            "Where this column came from (csv file name or SQL table). "
            "Used to support multi-CSV/multi-table datasets without a complex wrapper type."
        ),
    )


class MissingnessSummary(BaseModel):
    overall_missing_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Share of missing cells across the entire dataset.",
    )
    columns_with_missing: int = Field(
        ...,
        description="Number of columns that have at least one missing value.",
    )
    high_missing_columns: List[str] = Field(
        default_factory=list,
        description="Columns with very high missingness (e.g., >50%).",
    )


class DomainSignals(BaseModel):
    """
    High-level signals to help the Analyzer & UI understand what kind of
    dataset this is and what dashboards make sense.
    """
    label_columns: List[str] = Field(
        default_factory=list,
        description="Columns that look like labels / targets.",
    )
    primary_label: Optional[str] = Field(
        default=None,
        description="Best candidate for the main label (e.g., churn_flag).",
    )
    date_columns: List[str] = Field(
        default_factory=list,
        description="Columns that appear to be dates or datetimes.",
    )
    identifier_columns: List[str] = Field(
        default_factory=list,
        description="Columns that act as entity IDs.",
    )

    has_time_series: bool = Field(
        default=False,
        description="True if time-series analysis seems meaningful.",
    )
    has_geolocation: bool = Field(
        default=False,
        description="True if geospatial fields (lat/lon, regions) are present.",
    )
    pii_detected: bool = Field(
        default=False,
        description="True if any likely PII was detected and handled.",
    )

    extra_tags: List[str] = Field(
        default_factory=list,
        description="Short tags describing domain context (e.g., 'credit_card', 'customer_level').",
    )


class CsvSourceInfo(BaseModel):
    file_name: str
    row_count: int
    column_count: int
    is_primary: bool = False


# ---------------------------------------------------------------------------
# Top-level DataProfile
# ---------------------------------------------------------------------------

class DataProfile(BaseModel):
    """
    Compact data profile produced by the Data Agent.

    - Scales to wide tables by limiting 'key_columns'
    - Rich enough to drive dashboard planning & UI decisions
    """
    dataset_overview: DatasetOverview
    key_columns: List[ColumnProfile] = Field(
        default_factory=list,
        description=(
            "Compact profiles for a small subset of important columns "
            "(e.g., identifiers, label, date columns, and top-N features)."
        ),
    )
    # Optional: total column names if you still want the full list without per-column stats
    all_column_names: List[str] = Field(
        default_factory=list,
        description="List of all column names in the cleaned dataset (no metadata).",
    )

    missingness: MissingnessSummary
    domain_signals: DomainSignals

    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal issues or caveats (e.g., 'no dates found', 'label very imbalanced').",
    )

    # For forward-compat: store anything extra without breaking the schema
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extension point for future fields; ignored by core agents.",
    )
