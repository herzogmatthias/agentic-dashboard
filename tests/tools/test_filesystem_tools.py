from types import SimpleNamespace
from pathlib import Path
import json

from src.tools.data_analyst.artifacts import (
    write_data_profile,
    write_cleaning_summary,
    write_metrics_summary,
)
from src.models.data_profile import DataProfile, DatasetOverview, MissingnessSummary, DomainSignals
from src.models.cleaning_summary import CleaningSummary, Shape
from src.models.metrics_summary import MetricsSummary


def _tc(state: dict):
    return SimpleNamespace(state=state)


def _minimal_data_profile() -> DataProfile:
    """Create a minimal valid DataProfile for testing."""
    return DataProfile(
        dataset_overview=DatasetOverview(
            row_count=100,
            column_count_raw=10,
            column_count_clean=10,
        ),
        missingness=MissingnessSummary(
            overall_missing_pct=5.0,
            columns_with_missing=2,
        ),
        domain_signals=DomainSignals(),
    )


def _minimal_cleaning_summary() -> CleaningSummary:
    """Create a minimal valid CleaningSummary for testing."""
    return CleaningSummary(
        original_shape=Shape(rows=100, columns=10),
        cleaned_shape=Shape(rows=100, columns=10),
    )


def _minimal_metrics_summary() -> MetricsSummary:
    """Create a minimal valid MetricsSummary for testing."""
    return MetricsSummary()


def test_write_profile_and_cleaning(tmp_path):
    state = {"run_dir": str(tmp_path)}
    p1 = write_data_profile(_minimal_data_profile(), _tc(state))
    p2 = write_cleaning_summary(_minimal_cleaning_summary(), _tc(state))
    assert Path(p1).exists() and Path(p2).exists()
    # Check they're JSON files now
    assert Path(p1).suffix == ".json"
    assert Path(p2).suffix == ".json"


def test_write_metrics_summary(tmp_path):
    state = {"run_dir": str(tmp_path)}
    p = write_metrics_summary(_minimal_metrics_summary(), _tc(state))
    assert Path(p).exists()
    # Metrics summary goes to run_dir directly as JSON
    assert Path(p).name == "metrics_summary.json"


def test_write_profile_accepts_dict(tmp_path):
    """Test that write_data_profile accepts dict input (ADK passes dicts from LLM)."""
    state = {"run_dir": str(tmp_path)}
    profile_dict = {
        "dataset_overview": {
            "row_count": 100,
            "column_count_raw": 10,
            "column_count_clean": 10,
        },
        "missingness": {
            "overall_missing_pct": 5.0,
            "columns_with_missing": 2,
        },
        "domain_signals": {},
    }
    p = write_data_profile(profile_dict, _tc(state))
    assert Path(p).exists()
    # Verify it's valid JSON
    content = json.loads(Path(p).read_text())
    assert content["dataset_overview"]["row_count"] == 100
