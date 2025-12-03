from types import SimpleNamespace
from pathlib import Path

from src.tools.orchestrator import (
    validate_dataset,
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
