from types import SimpleNamespace
from pathlib import Path

from src.tools.planner import create_dashboard
from src.models.dashboard_concept_lite import DashboardConceptLite, KpiSpec, VisualSpec, MeasureSpec, DimensionSpec


def _tc(state: dict):
    return SimpleNamespace(state=state)


def test_create_dashboard_writes_file(tmp_path):
    state = {"run_dir": str(tmp_path)}
    concept = DashboardConceptLite(
        title="Demo",
        description="Test",
        audience="manager",
        primary_use_case="monitoring",
        layout_description="header + two charts",
        kpis=[KpiSpec(id="k1", title="KPI 1", description="desc", formula="a/b")],
        visuals=[
            VisualSpec(
                id="v1",
                title="Chart",
                purpose="insight",
                type="bar",
                measures=[MeasureSpec(column_or_kpi="col")],
                dimensions=[DimensionSpec(column="dim")],
            )
        ],
        global_filters=[],
        limitations=[],
    )
    msg = create_dashboard(concept, _tc(state))
    out_path = Path(tmp_path) / "planner" / "dashboard_concept.json"
    assert out_path.exists(), f"Expected file to exist: {out_path}"
    assert "Dashboard concept written" in msg
