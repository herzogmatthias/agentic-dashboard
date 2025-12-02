from types import SimpleNamespace
from pathlib import Path

from src.tools.orchestrator import (
    validate_dataset,
    prepare_data_analysis,
    prepare_planner,
    read_state,
    write_user_goals,
)


def _tc(state: dict):
    return SimpleNamespace(state=state)


def test_validate_dataset_with_tempfile(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    out = validate_dataset(str(p), _tc({}))
    assert out["valid"] is True
    assert "validated" in out["message"].lower()


def test_prepare_data_analysis_requires_run_dir_and_dataset():
    state = {"run_dir": "x", "dataset_path": "y"}
    out = prepare_data_analysis("do things", _tc(state))
    assert out["ready"] is True
    assert state.get("temp:data_analysis_instructions") == "do things"


def test_prepare_planner_requires_data_analysis_output():
    state = {"data_analysis_output": {"success": True}}
    out = prepare_planner("handoff text", _tc(state))
    assert out["ready"] is True
    assert state.get("temp:planner_handoff") == "handoff text"


def test_read_state_allows_only_whitelist():
    state = {"user_goals": {}, "dataset_path": "x"}
    ok = read_state("user_goals", _tc(state))
    assert ok["found"] is True and ok["value"] == {}
    bad = read_state("secret", _tc(state))
    assert bad["found"] is False and "allowed" in bad["message"].lower()


def test_write_user_goals_sets_state():
    state = {}
    out = write_user_goals("goal", "aud", "use", "a,b,c", _tc(state))
    assert out["success"] is True
    assert state["user_goals"]["constraints"] == ["a", "b", "c"]
