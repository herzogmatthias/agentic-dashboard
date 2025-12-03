from types import SimpleNamespace
from pathlib import Path
import json

from src.tools.filesystem import (
    write_data_profile,
    write_cleaning_summary,
    write_metrics_summary,
    inspect_json_keys,
    inspect_json_value,
    read_snippet,
)


def _tc(state: dict):
    return SimpleNamespace(state=state)


def test_write_profile_and_cleaning(tmp_path):
    state = {"run_dir": str(tmp_path)}
    p1 = write_data_profile("# profile", _tc(state))
    p2 = write_cleaning_summary("# cleaning", _tc(state))
    assert Path(p1).exists() and Path(p2).exists()


def test_write_metrics_summary(tmp_path):
    state = {"run_dir": str(tmp_path)}
    p = write_metrics_summary("# metrics", _tc(state))
    assert Path(p).exists()
    # Metrics summary goes to run_dir directly (not cleaned subdirectory)
    assert Path(p).name == "metrics_summary.md"


def test_inspect_json_keys_and_value(tmp_path):
    data = {"a": {"b": [1,2,3], "c": {"d": 5}}, "e": [ {"x": 1} ]}
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    keys = inspect_json_keys(str(path), max_depth=3)
    assert any(k.startswith("a.b") for k in keys["structure"])  # flattens nested
    val = inspect_json_value(str(path), "a.c.d")
    assert json.loads(val["value"]) == 5


def test_read_snippet_local(tmp_path):
    f = tmp_path / "log.txt"
    lines = [f"line {i}" for i in range(1, 21)]
    f.write_text("\n".join(lines), encoding="utf-8")
    out = read_snippet(str(f), 5, 8)
    assert out["file_lines"] == 20
    assert out["snippet"].splitlines()[0] == "line 5"
