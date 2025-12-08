"""
Shared fixtures for backend tools tests.
"""
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.tools.backend_dev.filesystem import SAMPLE_DASHBOARD_ROOT


def make_tool_context(state: dict[str, Any]) -> SimpleNamespace:
    """Create a mock ToolContext with the given state."""
    return SimpleNamespace(state=state)


@pytest.fixture
def sample_dashboard_path() -> Path:
    """Return the path to the sample-dashboard project."""
    return SAMPLE_DASHBOARD_ROOT


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    """Create a temporary run directory structure for testing.
    
    Structure mirrors actual run directory layout:
    - {run_dir}/cleaned/                <- cleaned data files
    - {run_dir}/data_profile.json       <- data profile JSON
    - {run_dir}/cleaning_summary.json   <- cleaning summary JSON
    - {run_dir}/planner/                <- planner outputs
    """
    # Create cleaned directory at root level (not under data_analysis)
    cleaned_dir = tmp_path / "cleaned"
    cleaned_dir.mkdir(parents=True)
    
    # Create sample data profile as JSON at root level
    profile_data = {
        "dataset_overview": {
            "row_count": 100,
            "column_count_raw": 5,
            "column_count_clean": 5,
            "new_columns": [],
            "notes": []
        },
        "key_columns": [],
        "all_column_names": ["id", "name", "value", "category", "date"],
        "missingness": {
            "overall_missing_pct": 2.5,
            "columns_with_missing": 1,
            "high_missing_columns": []
        },
        "domain_signals": {
            "label_columns": [],
            "date_columns": ["date"],
            "identifier_columns": ["id"],
            "has_time_series": False,
            "has_geolocation": False,
            "pii_detected": False,
            "extra_tags": []
        },
        "warnings": [],
        "extra": {}
    }
    profile_path = tmp_path / "data_profile.json"
    profile_path.write_text(json.dumps(profile_data), encoding="utf-8")
    
    # Create sample cleaned CSV
    csv_path = cleaned_dir / "cleaned.csv"
    csv_path.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300", encoding="utf-8")
    
    # Create planner subdirectory with dashboard concept
    planner_dir = tmp_path / "planner"
    planner_dir.mkdir(parents=True)
    
    concept = {
        "goal": "Sales Dashboard",
        "kpis": [{"name": "total_revenue", "formula": "SUM(revenue)"}],
        "visuals": [{"id": "chart1", "type": "bar"}],
    }
    concept_path = planner_dir / "dashboard_concept.json"
    concept_path.write_text(json.dumps(concept), encoding="utf-8")
    
    return tmp_path


@pytest.fixture
def temp_csv(tmp_path: Path) -> Path:
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"
    rows = ["col_a,col_b,col_c"]
    for i in range(10):
        rows.append(f"val_{i},data_{i},{i * 100}")
    csv_path.write_text("\n".join(rows), encoding="utf-8")
    return csv_path


def patch_allowed_paths_for_temp(dest_root: Path) -> list[str]:
    """Generate ALLOWED_PATHS list for a temporary test directory."""
    return [
        str(dest_root / "src" / "app" / "api"),
        str(dest_root / "src" / "models"),
        str(dest_root / "src" / "lib"),
        str(dest_root / "data"),
    ]
